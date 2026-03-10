"""Image extraction module for extracting images from PDF papers."""

import hashlib
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image

from models import Paper, PaperStatus, ImageMetadata


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
            # Reset seen hashes for this paper
            self._seen_hashes.clear()

            # Open PDF
            doc = fitz.open(str(paper.pdf_path))

            # Create output directory for this paper
            paper_output_dir = self.output_dir / paper.arxiv_id
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

                        # Convert to PIL Image and save
                        pil_image = Image.frombytes(
                            mode="RGB",
                            size=(width, height),
                            data=image_data,
                        )
                        pil_image.save(image_path)

                        # Create metadata
                        metadata = ImageMetadata(
                            path=image_path,
                            page_number=page.number + 1,  # 1-based page numbers
                        )

                        paper.images.append(metadata)
                        extracted_count += 1

                    except Exception:
                        # Skip individual image extraction errors
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

        except Exception:
            paper.status = PaperStatus.failed
            return paper
