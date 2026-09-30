"""Render a formatted DOCX to PDF, page images, and page-aligned TTS text."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import fitz

try:
    from .prepare_book import extract_pages, join_pages_for_tts
    from .text_normalize import match_text
except ImportError:
    from prepare_book import extract_pages, join_pages_for_tts
    from text_normalize import match_text


def find_libreoffice() -> str:
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if not executable:
        raise SystemExit("LibreOffice not found. Install libreoffice-writer on AutoDL to render DOCX pages.")
    return executable


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a DOCX into page images and page-aligned TTS text.")
    parser.add_argument("--docx", required=True)
    parser.add_argument("--pdf-output", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--text-output", required=True)
    parser.add_argument("--pages-output", required=True)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()

    docx_path = Path(args.docx).resolve()
    pdf_path = Path(args.pdf_output).resolve()
    images_dir = Path(args.images_dir).resolve()
    text_output = Path(args.text_output).resolve()
    pages_output = Path(args.pages_output).resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    text_output.parent.mkdir(parents=True, exist_ok=True)
    pages_output.parent.mkdir(parents=True, exist_ok=True)
    for stale_image in images_dir.glob("page_*.png"):
        stale_image.unlink()

    rendered_pdf = pdf_path.parent / f"{docx_path.stem}.pdf"
    if rendered_pdf.exists():
        rendered_pdf.unlink()
    subprocess.run(
        [find_libreoffice(), "--headless", "--convert-to", "pdf", "--outdir", str(pdf_path.parent), str(docx_path)],
        check=True,
    )
    if not rendered_pdf.is_file():
        raise SystemExit(f"LibreOffice did not create the expected PDF: {rendered_pdf}")
    if rendered_pdf != pdf_path:
        shutil.copy2(rendered_pdf, pdf_path)

    pages, checklist = extract_pages(pdf_path)
    scale = args.dpi / 72.0
    with fitz.open(pdf_path) as document:
        if len(document) != len(pages):
            raise ValueError(f"PDF rendering has {len(document)} pages but extraction returned {len(pages)} pages")
        for index, page in enumerate(document, 1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            pixmap.save(images_dir / f"page_{index:04d}.png")

    text_output.write_text(join_pages_for_tts(pages) + "\n", encoding="utf-8")
    payload = {
        "source_docx": str(docx_path),
        "pdf": str(pdf_path),
        "page_count": len(pages),
        "checklist": checklist,
        "pages": [
            {"page": index, "image": f"page_{index:04d}.png", "text": text, "match_text": match_text(text)}
            for index, text in enumerate(pages, 1)
        ],
    }
    pages_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    checklist_output = pages_output.with_name("book_checklist.json")
    checklist_output.write_text(json.dumps({"items": checklist}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rendered {len(pages)} pages: {pdf_path}")
    print(f"Created {len(pages)} page images in {images_dir}")
    print(f"Wrote page-aligned text to {text_output}; checklist: {checklist_output}")


if __name__ == "__main__":
    main()
