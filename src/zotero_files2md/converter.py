"""Attachment-to-Markdown conversion helpers using Docling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from docling.document_converter import DocumentConverter

from .models import AttachmentMetadata
from .settings import ExportSettings
from .utils import ensure_directory, get_logger, slugify

logger = get_logger()


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

    output_dir = ensure_directory(
        settings.output_dir
        / slugify(attachment.parent_title, attachment.parent_item_key or "item")
    )

    filename_base = slugify(attachment.title, attachment.attachment_key)
    output_path = output_dir / f"{filename_base}.md"

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

    if not file_path.exists():
        msg = f"File not found for conversion: {file_path}"
        raise FileNotFoundError(msg)

    try:
        markdown = _render_markdown(file_path, settings.markdown_options)
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


def _render_markdown(file_path: Path, markdown_options: dict[str, Any]) -> str:
    """Render a local document to Markdown using Docling.

    Currently ``markdown_options`` is accepted for forward compatibility but
    not actively mapped into Docling's configuration.
    """
    converter = DocumentConverter()
    result = converter.convert(str(file_path))

    if result.document is None:
        msg = f"Docling conversion failed for {file_path}: {result.status}"
        raise RuntimeError(msg)

    return result.document.export_to_markdown()
