"""Markdown generation module."""

import re
from datetime import datetime
from pathlib import Path

from models import Paper


class MarkdownRenderer:
    """Renders papers as Markdown documents."""

    def __init__(self, output_dir: Path, project_root: Path | None = None) -> None:
        """Initialize renderer with output directory.

        Args:
            output_dir: Directory where markdown files will be saved.
            project_root: Project root directory for calculating relative paths.
                         If None, uses output_dir's parent's parent.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Calculate project root for relative path calculations
        # Assuming structure: project_root/data/summaries/
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Go up two levels from data/summaries/ to project root
            self.project_root = self.output_dir.parent.parent

    def render(self, paper: Paper) -> Path:
        """Render paper as Markdown file."""
        filename = self._sanitize_filename(f"{paper.arxiv_id}_{paper.title[:50]}")
        output_path = self.output_dir / f"{filename}.md"

        content = self._generate_content(paper, output_path)
        output_path.write_text(content)

        return output_path

    def _sanitize_filename(self, filename: str) -> str:
        """Remove special characters from filename."""
        # Replace special chars with underscore
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple spaces
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Limit length
        return sanitized[:100]

    def _add_dict_content(self, lines: list, data: dict, indent: int = 0):
        """Add dict content to lines list recursively."""
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{'  ' * indent}**{key}**:")
                self._add_dict_content(lines, value, indent + 1)
            elif isinstance(value, list):
                lines.append(f"{'  ' * indent}**{key}**:")
                for item in value:
                    if isinstance(item, dict):
                        self._add_dict_content(lines, item, indent + 1)
                    else:
                        lines.append(f"{'  ' * (indent + 1)}- {item}")
            else:
                lines.append(f"{'  ' * indent}**{key}**: {value}")

    def _get_relative_image_path(self, image_path: Path, markdown_path: Path) -> str:
        """Calculate relative path from markdown file to image.

        Args:
            image_path: Absolute or relative path to image.
            markdown_path: Path where markdown file will be saved.

        Returns:
            Relative path string from markdown file to image.
        """
        image_path = Path(image_path)
        markdown_dir = markdown_path.parent

        # If image_path is relative, make it absolute relative to project root
        if not image_path.is_absolute():
            image_path = self.project_root / image_path

        # Use os.path.relpath to calculate relative path
        import os
        return os.path.relpath(image_path, markdown_dir)

    def _generate_content(self, paper: Paper, markdown_path: Path) -> str:
        """Generate Markdown content."""
        lines = []

        # Title
        lines.append(f"# {paper.title}")
        lines.append("")

        # Metadata section
        lines.append("## Metadata")
        lines.append(f"- **arXiv ID**: {paper.arxiv_id}")
        lines.append(f"- **Authors**: {', '.join(paper.authors)}")
        lines.append(f"- **Submitted**: {paper.submitted_date.strftime('%Y-%m-%d')}")
        lines.append(f"- **Categories**: {', '.join(paper.categories)}")
        if paper.pdf_path:
            lines.append(f"- **PDF**: `{paper.pdf_path}`")
        lines.append(f"- **URL**: {paper.pdf_url}")
        lines.append("")

        # Abstract section
        lines.append("## Abstract")
        lines.append(paper.abstract)
        lines.append("")

        # Summary section (if available)
        if paper.summary:
            lines.append("## Summary")

            # Check if it's multi-step summary (dict with step keys)
            if any(step in paper.summary for step in ["screening", "quick", "deep", "experiments", "reproducibility", "inspiration"]):
                # Multi-step format
                step_titles = {
                    "screening": "粗筛",
                    "quick": "粗读",
                    "deep": "精读",
                    "experiments": "实验分析",
                    "reproducibility": "复现/落地",
                    "inspiration": "研究启发",
                }

                for step, title in step_titles.items():
                    if step in paper.summary and paper.summary[step]:
                        lines.append(f"### {title}")
                        step_data = paper.summary[step]
                        self._add_dict_content(lines, step_data)
                        lines.append("")
            else:
                # Single-step format (original)
                def add_field(key: str, title: str = None):
                    if key in paper.summary and paper.summary[key]:
                        title = title or key.replace("_", " ").title()
                        lines.append(f"### {title}")
                        val = paper.summary[key]
                        # Handle dict (like experiments)
                        if isinstance(val, dict):
                            for k, v in val.items():
                                lines.append(f"**{k}**: {v}")
                        # Handle list (like contributions, keywords)
                        elif isinstance(val, list):
                            for item in val:
                                lines.append(f"- {item}")
                        # Handle string
                        else:
                            lines.append(str(val))
                        lines.append("")

                # Add fields in order
                add_field("research_problem")
                add_field("motivation")
                add_field("core_method")
                add_field("model_io")
                add_field("contributions")
                add_field("experiments")
                add_field("limitations")
                add_field("potential_risks")
                add_field("keywords")
                add_field("applicable_scenarios")
                add_field("figures")
        else:
            lines.append("## Summary")
            lines.append("*No summary available.*")
            lines.append("")

        # Images section (if available)
        if paper.images:
            lines.append("## Figures and Tables")
            lines.append("")

            for image in paper.images:
                # Get fig_type, default to "Figure" if None
                fig_type = image.fig_type if image.fig_type else "Figure"

                # Create heading with figure/table type and number
                if image.figure_number:
                    lines.append(f"### {fig_type} {image.figure_number}")
                else:
                    lines.append(f"### {fig_type}")

                # Calculate relative path for markdown link
                relative_image_path = self._get_relative_image_path(image.path, markdown_path)

                # Add image markdown
                lines.append(f"![{fig_type} {image.figure_number or ''}]({relative_image_path})")
                lines.append("")

                # Add caption in italics if it exists
                if image.caption:
                    lines.append(f"*{image.caption}*")
                    lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Generated by Paper Daily on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        return "\n".join(lines)
