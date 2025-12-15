"""Attachment-to-Markdown conversion helpers using Docling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import local
from typing import Literal

from .models import AttachmentMetadata
from .settings import ExportSettings
from .utils import compute_output_path, ensure_directory, get_logger

logger = get_logger()
_converter_local = local()


def convert_attachment_to_markdown(
    attachment: AttachmentMetadata,
    file_path: Path,
    settings: ExportSettings,
) -> "ConversionResult":
    """Convert a Zotero attachment to a Markdown file using Docling.

    Args:
        attachment: Attachment metadata describing the file to convert.
        file_path: Path to a local file downloaded from the Zotero API.
        settings: Export configuration specifying output directory and options.

    Returns:
        A :class:`ConversionResult` describing the export outcome.
    """
    logger.debug(
        "Converting attachment %s using file %s", attachment.attachment_key, file_path
    )

    output_path = compute_output_path(attachment, settings.output_dir)

    if output_path.exists() and not settings.overwrite:
        logger.info("Skipping existing file: %s", output_path)
        return ConversionResult(
            source=file_path,
            output=output_path,
            status="skipped",
        )

    if settings.dry_run:
        logger.info("[dry-run] Would write %s", output_path)
        return ConversionResult(
            source=file_path,
            output=output_path,
            status="dry-run",
        )

    ensure_directory(output_path.parent)

    if not file_path.exists():
        msg = f"File not found for conversion: {file_path}"
        raise FileNotFoundError(msg)

    try:
        markdown = _render_markdown(file_path, settings)
        output_path.write_bytes(markdown.encode("utf-8"))
        logger.info("Wrote %s", output_path)
    except Exception as exc:
        logger.error("Error converting %s: %s", file_path, exc, exc_info=True)
        return ConversionResult(
            source=file_path,
            output=output_path,
            status="skipped",
        )
    return ConversionResult(
        source=file_path,
        output=output_path,
        status="converted",
    )


@dataclass(slots=True, frozen=True)
class ConversionResult:
    """Describe the outcome of converting a single attachment."""

    source: Path
    output: Path
    status: Literal["converted", "skipped", "dry-run"]


def get_pipeline_options(
    force_full_page_ocr: bool,
    do_picture_description: bool,
    image_resolution_scale: float,
    device: AcceleratorDevice | None = None,
    num_threads: int = 4,
) -> PdfPipelineOptions:
    from docling.datamodel.pipeline_options import (
        AcceleratorDevice,
        AcceleratorOptions,
        PdfPipelineOptions,
        TableFormerMode,
    )

    if device is None:
        device = AcceleratorDevice.AUTO

    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    pipeline_options.do_picture_description = do_picture_description
    pipeline_options.do_formula_enrichment = True
    pipeline_options.do_code_enrichment = True
    pipeline_options.ocr_options.force_full_page_ocr = force_full_page_ocr
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.images_scale = image_resolution_scale

    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=num_threads, device=device
    )
    return pipeline_options


def _render_markdown(
    file_path: Path,
    settings: ExportSettings,
    device: AcceleratorDevice | None = None,
) -> str:
    """Render a local document to Markdown using Docling."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import AcceleratorDevice
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc.base import ImageRefMode

    if device is None:
        device = AcceleratorDevice.AUTO

    cache_key = (
        settings.force_full_page_ocr,
        settings.do_picture_description,
        settings.image_resolution_scale,
        device,
    )
    cached_key = getattr(_converter_local, "key", None)
    converter = getattr(_converter_local, "converter", None)

    if converter is None or cached_key != cache_key:
        pipeline_options = get_pipeline_options(
            force_full_page_ocr=settings.force_full_page_ocr,
            do_picture_description=settings.do_picture_description,
            image_resolution_scale=settings.image_resolution_scale,
            device=device,
        )
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        _converter_local.key = cache_key
        _converter_local.converter = converter

    result = converter.convert(str(file_path))

    if result.document is None:
        msg = f"Docling conversion failed for {file_path}: {result.status}"
        raise RuntimeError(msg)

    # Use ImageRefMode.EMBEDDED as per reference
    return result.document.export_to_markdown(
        image_mode=ImageRefMode.EMBEDDED,
        page_break_placeholder="\n\n--- Page Break ---\n\n",
    )
