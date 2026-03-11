"""Factory for creating image extractor instances."""

from pathlib import Path
from typing import Any

from image_extractor import ImageExtractor
from pdffigures_extractor import PDFFigures2Extractor


class ExtractorFactory:
    """Factory for creating image extractor instances based on configuration.

    This factory supports creating different extractor types:
    - "pymupdf": Uses PyMuPDF (fitz) for basic image extraction
    - "pdffigures2": Uses pdffigures2 JAR for advanced figure/table extraction

    The factory defaults to "pymupdf" for backward compatibility.
    """

    @staticmethod
    def create(config: dict[str, Any] | Any, output_dir: Path) -> ImageExtractor | PDFFigures2Extractor:
        """Create an extractor instance based on the provided configuration.

        Args:
            config: Configuration as a dict or VisionConfig object.
            output_dir: Directory where extracted images should be saved.

        Returns:
            An instance of ImageExtractor or PDFFigures2Extractor.

        Raises:
            ValueError: If pdffigures2 is selected but pdffigures2_jar is not configured.
        """
        # Handle both dict and VisionConfig objects
        if isinstance(config, dict):
            extractor_type = config.get("extractor", "pymupdf")
        else:
            # Assume it's a VisionConfig object with attributes
            extractor_type = getattr(config, "extractor", "pymupdf")

        # Route to appropriate factory method
        if extractor_type == "pdffigures2":
            return ExtractorFactory._create_pdffigures2_extractor(config, output_dir)
        else:  # Default to pymupdf
            return ExtractorFactory._create_pymupdf_extractor(config, output_dir)

    @staticmethod
    def _create_pymupdf_extractor(config: dict[str, Any] | Any, output_dir: Path) -> ImageExtractor:
        """Create a PyMuPDF-based image extractor.

        Args:
            config: Configuration as a dict or VisionConfig object.
            output_dir: Directory where extracted images should be saved.

        Returns:
            An ImageExtractor instance.
        """
        # Extract extraction config
        if isinstance(config, dict):
            extraction_config = config.get("extraction", {})
        else:
            # Assume it's a VisionConfig object
            extraction_config = getattr(config, "extraction", None)
            if extraction_config is not None:
                extraction_config = extraction_config.model_dump()
            else:
                extraction_config = {}

        # Create ImageExtractor with extracted config
        return ImageExtractor(
            min_size=tuple(extraction_config.get("min_size", (200, 200))),
            max_aspect_ratio=extraction_config.get("max_aspect_ratio", 3.0),
            max_images_per_paper=extraction_config.get("max_images_per_paper", 20),
            skip_duplicates=extraction_config.get("skip_duplicates", True),
            output_dir=output_dir,
        )

    @staticmethod
    def _create_pdffigures2_extractor(config: dict[str, Any] | Any, output_dir: Path) -> PDFFigures2Extractor:
        """Create a pdffigures2-based figure extractor.

        Args:
            config: Configuration as a dict or VisionConfig object.
            output_dir: Directory where extracted figures should be saved.

        Returns:
            A PDFFigures2Extractor instance.

        Raises:
            ValueError: If pdffigures2_jar is not configured.
        """
        # Extract jar_path
        if isinstance(config, dict):
            jar_path_str = config.get("pdffigures2_jar")
        else:
            # Assume it's a VisionConfig object
            jar_path_str = getattr(config, "pdffigures2_jar", None)

        # Validate jar_path is configured
        if not jar_path_str:
            raise ValueError(
                "pdffigures2_jar must be configured to use pdffigures2 extractor. "
                "Please provide the path to the pdffigures2 JAR file."
            )

        jar_path = Path(jar_path_str)

        # Extract additional config options
        if isinstance(config, dict):
            dpi = config.get("pdffigures2_dpi", 150)
            extract_figures = config.get("pdffigures2_extract_figures", True)
            extract_tables = config.get("pdffigures2_extract_tables", True)
            max_figures = config.get("pdffigures2_max_figures", 20)
            java_options = config.get("pdffigures2_java_options", None)
        else:
            # Assume it's a VisionConfig object
            dpi = getattr(config, "pdffigures2_dpi", 150)
            extract_figures = getattr(config, "pdffigures2_extract_figures", True)
            extract_tables = getattr(config, "pdffigures2_extract_tables", True)
            max_figures = getattr(config, "pdffigures2_max_figures", 20)
            java_options = getattr(config, "pdffigures2_java_options", None)

        # Create PDFFigures2Extractor
        return PDFFigures2Extractor(
            jar_path=jar_path,
            output_dir=output_dir,
            dpi=dpi,
            extract_figures=extract_figures,
            extract_tables=extract_tables,
            max_figures=max_figures,
            java_options=java_options,
        )
