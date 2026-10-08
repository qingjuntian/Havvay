"""Render a formatted DOCX to a fixed PDF, page images, and page-aligned TTS text."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

try:
    from .prepare_book import extract_page_records, join_pages_for_tts
except ImportError:
    from prepare_book import extract_page_records, join_pages_for_tts


def convert_docx_to_pdf(docx: Path, pdf_output: Path) -> None:
    office = shutil.which("libreoffice") or shutil.which("soffice")
    if office is None:
        raise RuntimeError("LibreOffice is required; install libreoffice-writer before processing DOCX files")
    if not docx.is_file():
        raise FileNotFoundError(f"DOCX file not found: {docx}")

    pdf_output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reading-docx-") as temporary_dir:
        result = subprocess.run(
            [office, "--headless", "--convert-to", "pdf", "--outdir", temporary_dir, str(docx)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        rendered_pdf = Path(temporary_dir) / f"{docx.stem}.pdf"
        if not rendered_pdf.is_file():
            details = " ".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
            raise RuntimeError(f"LibreOffice did not create a PDF{': ' + details if details else ''}")
        shutil.copy2(rendered_pdf, pdf_output)


def render_page_images(pdf: Path, images_dir: Path, dpi: int = 160) -> int:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Install PyMuPDF (pymupdf) to render PDF pages to PNG") from exc

    images_dir.mkdir(parents=True, exist_ok=True)
    for old_image in images_dir.glob("page_*.png"):
        old_image.unlink()
    scale = dpi / 72
    with fitz.open(pdf) as document:
        for index, page in enumerate(document, 1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            pixmap.save(images_dir / f"page_{index:04d}.png")
        return len(document)


def prepare_docx(docx: Path, pdf_output: Path, images_dir: Path, text_output: Path, pages_output: Path) -> int:
    convert_docx_to_pdf(docx, pdf_output)
    rendered_page_count = render_page_images(pdf_output, images_dir)
    pages, checklist = extract_page_records(pdf_output)
    if rendered_page_count != len(pages):
        raise RuntimeError(
            f"PDF renderer produced {rendered_page_count} images but text extraction found {len(pages)} pages"
        )

    text_output.parent.mkdir(parents=True, exist_ok=True)
    pages_output.parent.mkdir(parents=True, exist_ok=True)
    text_output.write_text(join_pages_for_tts([page["text"] for page in pages]) + "\n", encoding="utf-8")
    pages_output.write_text(
        json.dumps(
            {"docx": str(docx), "pdf": str(pdf_output), "checklist": checklist, "pages": pages},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    checklist_output = pages_output.with_name("book_checklist.json")
    checklist_output.write_text(json.dumps({"items": checklist}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(pages)} pages: {pdf_output}, {images_dir}, {text_output}")
    return len(pages)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a fixed-layout DOCX for page-aligned TTS and video.")
    parser.add_argument("--docx", required=True)
    parser.add_argument("--pdf-output", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--text-output", required=True)
    parser.add_argument("--pages-output", required=True)
    args = parser.parse_args()
    prepare_docx(
        Path(args.docx).resolve(),
        Path(args.pdf_output).resolve(),
        Path(args.images_dir).resolve(),
        Path(args.text_output).resolve(),
        Path(args.pages_output).resolve(),
    )


if __name__ == "__main__":
    main()