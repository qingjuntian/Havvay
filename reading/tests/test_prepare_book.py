from __future__ import annotations

import tempfile
import unittest
import importlib
import importlib.util
from pathlib import Path

fitz = importlib.import_module("fitz") if importlib.util.find_spec("fitz") else None

from src.prepare_book import extract_page_records, reconcile_page_breaks, render_page_images


class PdfPreparationTests(unittest.TestCase):
    def test_reconciles_page_breaks_to_complete_sentences(self) -> None:
        pages = reconcile_page_breaks(["上一句完成。社会工作称为社", "会工作服务。下一句开始"])

        self.assertEqual("".join(pages), "上一句完成。社会工作称为社会工作服务。下一句开始")
        self.assertTrue(all(page.endswith(("。", "！", "？", "!", "?", "；", ";")) for page in pages[:-1]))
        self.assertEqual(len(pages), 2)

    def test_reconciles_page_breaks_at_enumeration_comma(self) -> None:
        pages = reconcile_page_breaks(["服务内容包括社", "会工作、社会政策和社区服务。后续内容"])

        self.assertTrue(pages[0].endswith("服务内容包括社会工作、"))
        self.assertTrue(pages[1].startswith("社会政策和社区服务。"))

    def test_reconciles_page_breaks_after_chinese_ellipsis(self) -> None:
        for ellipsis in ("……", "…"):
            with self.subTest(ellipsis=ellipsis):
                pages = reconcile_page_breaks(["说明情况", f"{ellipsis}随后继续。"])

                self.assertTrue(pages[0].endswith(ellipsis))
                self.assertTrue(pages[1].startswith("随后继续。"))

    def test_reconciliation_keeps_page_final_heading_after_neighbor_moves(self) -> None:
        pages = [
            "上一句。专业社会工作称为社",
            "会工作服务。下面说明目标。\n\n（一）目标标题",
            "下一页正文开始。",
        ]

        reconciled = reconcile_page_breaks(pages)

        self.assertTrue(reconciled[0].endswith("专业社会工作称为社会工作服务。"))
        self.assertIn("（一）目标标题", reconciled[1])
        self.assertTrue(reconciled[2].startswith("下一页正文开始。"))

    def test_reconciliation_moves_only_short_page_spills(self) -> None:
        pages = reconcile_page_breaks([
            "第一页正文称为社",
            "会工作服务。第二页正文结束，社会有责任帮",
            "助他们解除危机，帮助他们生存下来、生活下去。第四页开始",
        ])

        self.assertTrue(pages[0].endswith("社会工作服务。"))
        self.assertTrue(pages[1].endswith("社会有责任帮助他们解除危机，"))
        self.assertTrue(pages[2].startswith("帮助他们生存下来、生活下去。第四页开始"))

    def test_long_continuation_stays_with_the_following_page(self) -> None:
        pages = reconcile_page_breaks([
            "第四页正文结束，服务对象的潜能",
            "使服务对象更好地解决困难、走出困境、重新面对生活。第五页正文开始。",
        ])

        self.assertTrue(pages[0].endswith("第四页正文结束，服务对象的潜能"))
        self.assertTrue(pages[1].startswith("使服务对象更好地解决困难、走出困境、重新面对生活。"))

    def test_page_leading_encyclopedia_citation_stays_on_its_source_page(self) -> None:
        pages = reconcile_page_breaks([
            "第十九页末句没有社会工作服务。",
            "《中国社会工作百科全书》指出，社会工作者是专业人员。",
        ])

        self.assertTrue(pages[0].endswith("没有社会工作服务。"))
        self.assertTrue(pages[1].startswith("《中国社会工作百科全书》指出，"))

    def test_rendered_images_and_extracted_text_match_pdf_pages(self) -> None:
        if fitz is None:
            self.skipTest("PyMuPDF is required for PDF rendering")
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