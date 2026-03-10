"""Image extraction module for extracting images from PDF papers."""

import asyncio
import hashlib
import logging
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from models import Paper, PaperStatus, ImageMetadata

logger = logging.getLogger(__name__)


def _sanitize_arxiv_id(arxiv_id: str) -> str:
    """Sanitize arxiv_id to prevent path traversal attacks.

    Args:
        arxiv_id: The arxiv ID to sanitize.

    Returns:
        Sanitized arxiv ID with only allowed characters.
    """
    # Only allow alphanumeric characters, dots, and dashes
    return "".join(c for c in arxiv_id if c.isalnum() or c in ".-")


class ImageExtractor:
    """Extracts images from PDF papers with smart filtering."""

    def __init__(
        self,
        min_size: tuple[int, int] = (200, 200),
        max_aspect_ratio: float = 3.0,
        max_images_per_paper: int = 20,
        skip_duplicates: bool = True,
        output_dir: Path = Path("data/images"),
    ) -> None:
        """Initialize the image extractor with filtering options.

        Args:
            min_size: Minimum width and height for images (width, height).
            max_aspect_ratio: Maximum aspect ratio (width/height or height/width).
            max_images_per_paper: Maximum number of images to extract per paper.
            skip_duplicates: Whether to skip duplicate images.
            output_dir: Directory to save extracted images.
        """
        self.min_size = min_size
        self.max_aspect_ratio = max_aspect_ratio
        self.max_images_per_paper = max_images_per_paper
        self.skip_duplicates = skip_duplicates
        self.output_dir = output_dir
        self._seen_hashes: set[str] = set()

    def _should_include_image(
        self, width: int, height: int, y_position_ratio: float
    ) -> bool:
        """Determine if an image should be included based on filtering criteria.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.
            y_position_ratio: Ratio of y position to page height (0-1).

        Returns:
            True if image should be included, False otherwise.
        """
        # Filter small images
        if width < self.min_size[0] or height < self.min_size[1]:
            return False

        # Filter extreme aspect ratios
        aspect_ratio = max(width / height, height / width)
        if aspect_ratio > self.max_aspect_ratio:
            return False

        # Filter header and footer (y position at edges)
        if y_position_ratio < 0.1 or y_position_ratio > 0.9:
            return False

        return True

    def _compute_image_hash(self, image_data: bytes) -> str:
        """Compute hash of image data for duplicate detection.

        Args:
            image_data: Raw image bytes.

        Returns:
            MD5 hash string of the image data.
        """
        return hashlib.md5(image_data).hexdigest()

    def _extract_caption(self, page, image_rect, search_radius: int = 200) -> tuple[str | None, str | None]:
        """Extract caption text near an image.

        Looks for text above and below the image that matches figure caption patterns.

        Args:
            page: PyMuPDF page object.
            image_rect: The bounding box of the image.
            search_radius: How far to search above/below the image (points).

        Returns:
            Tuple of (figure_number, caption_text) or (None, None).
        """
        import re

        # Caption patterns for English and Chinese
        caption_patterns = [
            r"(?i)Figure\s*\.?\s*(\d+[\w]?)[.:\s]",
            r"(?i)Fig\.\s*(\d+[\w]?)[.:\s]",
            r"(?i)图\s*\.?\s*(\d+[\w]?)[.:\s]",
            r"(?i)表\s*\.?\s*(\d+[\w]?)[.:\s]",  # Table in Chinese
            r"\(([a-z])\)",  # Sub-figure labels like (a), (b)
        ]

        # Get text above the image - larger area
        above_rect = fitz.Rect(
            image_rect.x0,
            max(0, image_rect.y0 - search_radius),
            image_rect.x1,
            image_rect.y0
        )
        above_text = page.get_text("text", clip=above_rect).strip()

        # Get text below the image
        below_rect = fitz.Rect(
            image_rect.x0,
            image_rect.y1,
            image_rect.x1,
            min(page.rect.y1, image_rect.y1 + search_radius)
        )
        below_text = page.get_text("text", clip=below_rect).strip()

        # Combine and search for caption
        combined_text = above_text + "\n" + below_text

        for pattern in caption_patterns:
            match = re.search(pattern, combined_text)
            if match:
                figure_num = match.group(1)
                # Extract the caption text (everything after the figure number)
                caption_start = match.end()
                # Get more text - up to 500 chars
                remaining = combined_text[caption_start:caption_start + 500]
                # Take first few lines
                caption_lines = remaining.split("\n")[:3]
                caption = " ".join(caption_lines).strip()
                # Clean up - remove extra whitespace and truncate
                caption = re.sub(r"\s+", " ", caption)[:300]
                return f"Figure {figure_num}", caption

        # If no caption pattern found, use first meaningful line from above text
        if above_text:
            lines = above_text.split("\n")
            for line in lines:
                line = line.strip()
                # Skip very short lines
                if len(line) > 10:
                    return None, line[:200]

        return None, None

    async def extract(self, paper: Paper) -> Paper:
        """Extract images from a paper's PDF.

        Args:
            paper: The paper to extract images from.

        Returns:
            The paper with extracted images metadata.
        """
        # Check if PDF path exists
        if not paper.pdf_path or not paper.pdf_path.exists():
            paper.status = PaperStatus.failed
            return paper

        try:
            # Run the blocking extraction in a thread pool
            return await asyncio.to_thread(self._extract_sync, paper)
        except Exception:
            logger.exception("Failed to extract images from paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper

    def _extract_sync(self, paper: Paper) -> Paper:
        """Synchronous image extraction (runs in thread pool).

        Args:
            paper: The paper to extract images from.

        Returns:
            The paper with extracted images metadata.
        """
        try:
            # Reset seen hashes for this paper
            self._seen_hashes.clear()

            # Open PDF
            doc = fitz.open(str(paper.pdf_path))

            # Create output directory for this paper - sanitize arxiv_id to prevent path traversal
            safe_arxiv_id = _sanitize_arxiv_id(paper.arxiv_id)
            paper_output_dir = self.output_dir / safe_arxiv_id
            paper_output_dir.mkdir(parents=True, exist_ok=True)

            extracted_count = 0
            page_count = 0

            # Iterate through pages
            for page in doc:
                page_count += 1
                page_height = page.rect.y1

                # Get images from page
                images = page.get_images()

                for img_idx, img in enumerate(images):
                    if extracted_count >= self.max_images_per_paper:
                        break

                    try:
                        # Extract image data
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_data = base_image["image"]

                        # Compute hash for duplicate detection
                        if self.skip_duplicates:
                            img_hash = self._compute_image_hash(image_data)
                            if img_hash in self._seen_hashes:
                                continue
                            self._seen_hashes.add(img_hash)

                        # Get image dimensions
                        width = base_image["width"]
                        height = base_image["height"]

                        # Get image position (y-coordinate)
                        # Try to get rect from get_image_rects, fallback to img tuple
                        try:
                            rects = page.get_image_rects(xref)
                            if rects:
                                y_position = rects[0].y0
                            else:
                                y_position = 0
                        except Exception:
                            y_position = 0

                        y_position_ratio = y_position / page_height if page_height > 0 else 0.5

                        # Apply smart filters
                        if not self._should_include_image(width, height, y_position_ratio):
                            continue

                        # Save image
                        image_filename = f"figure_{page.number}_{img_idx}.png"
                        image_path = paper_output_dir / image_filename

                        # Try to save image - handle various formats
                        try:
                            # First try: direct save from raw data if format is known
                            ext = base_image.get("ext", "")

                            # For PNG, we can often save directly
                            if ext == "png":
                                with open(image_path, "wb") as f:
                                    f.write(image_data)
                            else:
                                # For other formats, try PIL conversion
                                from io import BytesIO

                                # Try different approaches for PIL conversion
                                try:
                                    pil_image = Image.open(BytesIO(image_data))
                                    # Convert to RGB if needed
                                    if pil_image.mode != "RGB":
                                        pil_image = pil_image.convert("RGB")
                                    pil_image.save(image_path, "PNG")
                                except Exception:
                                    # Last resort: try frombytes with image data
                                    if len(image_data) >= width * height * 3:
                                        pil_image = Image.frombytes(
                                            mode="RGB",
                                            size=(width, height),
                                            data=image_data,
                                        )
                                        pil_image.save(image_path, "PNG")
                                    else:
                                        # Skip this image - not enough data
                                        continue
                        except Exception as e:
                            logger.debug(f"Skipping image {img_idx} on page {page.number}: {e}")
                            continue

                        # Extract caption if available
                        figure_number = None
                        caption = None
                        try:
                            if rects:
                                figure_number, caption = self._extract_caption(page, rects[0])
                        except Exception:
                            pass

                        # Create metadata
                        metadata = ImageMetadata(
                            path=image_path,
                            page_number=page.number + 1,  # 1-based page numbers
                            figure_number=figure_number,
                            caption=caption,
                        )

                        paper.images.append(metadata)
                        extracted_count += 1

                    except Exception as e:
                        # Log individual image extraction errors and skip
                        logger.warning(
                            "Failed to extract image %d from page %d of paper %s: %s",
                            img_idx,
                            page.number,
                            paper.arxiv_id,
                            e,
                        )
                        continue

                if extracted_count >= self.max_images_per_paper:
                    break

            doc.close()

            # Update paper status
            if extracted_count > 0:
                paper.status = PaperStatus.images_extracted
            else:
                # Even if no images found, mark as extracted (not failed)
                paper.status = PaperStatus.images_extracted

            return paper

        except FileNotFoundError as e:
            logger.error("PDF file not found for paper %s: %s", paper.arxiv_id, e)
            paper.status = PaperStatus.failed
            return paper
        except PermissionError as e:
            logger.error("Permission denied accessing PDF for paper %s: %s", paper.arxiv_id, e)
            paper.status = PaperStatus.failed
            return paper
        except OSError as e:
            logger.error("OS error processing PDF for paper %s: %s", paper.arxiv_id, e)
            paper.status = PaperStatus.failed
            return paper
        except Exception:
            logger.exception("Unexpected error extracting images from paper %s", paper.arxiv_id)
            paper.status = PaperStatus.failed
            return paper
