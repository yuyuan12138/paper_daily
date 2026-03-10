"""PDF text extraction module."""

import re
from pathlib import Path

from pypdf import PdfReader

from models import Paper, PaperStatus


class PDFParser:
    """Extracts text content from PDF files."""

    async def parse(self, paper: Paper) -> Paper:
        """Extract text from paper's PDF file."""
        if not paper.pdf_path or not paper.pdf_path.exists():
            paper.status = PaperStatus.failed
            return paper

        try:
            reader = PdfReader(str(paper.pdf_path))
            text_parts = []

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            if text_parts:
                full_text = "\n\n".join(text_parts)
                # Clean up excessive whitespace
                full_text = re.sub(r"\n{3,}", "\n\n", full_text)
                full_text = re.sub(r" +", " ", full_text)
                paper.parsed_text = full_text.strip()
            else:
                # Fallback to abstract if no text extracted
                paper.parsed_text = paper.abstract

            paper.status = PaperStatus.parsed
            return paper

        except Exception as e:
            # Mark as failed on any parsing error
            paper.status = PaperStatus.failed
            return paper
