from __future__ import annotations

import tempfile
import unittest
import importlib
import importlib.util
from pathlib import Path

fitz = importlib.import_module("fitz") if importlib.util.find_spec("fitz") else None

from src.prepare_book import extract_page_records, reconcile_page_breaks, render_page_images


@unittest.skipIf(fitz is None, "PyMuPDF is required for PDF rendering")
class PdfPreparationTests(unittest.TestCase):
    def test_reconciles_page_breaks_to_complete_sentences(self) -> None:
        pages = reconcile_page_breaks(["上一句完成。社会工作称为社", "会工作服务。下一句开始"])

        self.assertEqual("".join(pages), "上一句完成。社会工作称为社会工作服务。下一句开始")
        self.assertTrue(all(page.endswith(("。", "！", "？", "!", "?", "；", ";")) for page in pages[:-1]))
        self.assertEqual(len(pages), 2)

    def test_rendered_images_and_extracted_text_match_pdf_pages(self) -> None:
        assert fitz is not None
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf_path = root / "book.pdf"
            images_dir = root / "pages"
            with fitz.open() as document:
                for page_text in ("First page", "Second page"):
                    page = document.new_page(width=595, height=842)
                    page.insert_text((72, 72), page_text)
                document.save(pdf_path)

            records, _ = extract_page_records(pdf_path)
            rendered_page_count = render_page_images(pdf_path, images_dir)
            image_paths = sorted(images_dir.glob("page_*.png"))

            self.assertEqual(rendered_page_count, 2)
            self.assertEqual(len(records), 2)
            self.assertEqual([path.name for path in image_paths], ["page_0001.png", "page_0002.png"])
            self.assertIn("First page", records[0]["raw_text"])
            self.assertIn("Second page", records[1]["raw_text"])
            self.assertTrue(all(path.stat().st_size > 0 for path in image_paths))


if __name__ == "__main__":
    unittest.main()