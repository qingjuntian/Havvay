from __future__ import annotations

import unittest

from src.text_normalize import normalize_text


class TextNormalizationTests(unittest.TestCase):
    def test_converts_years_ages_ranges_and_percentages(self) -> None:
        self.assertEqual(normalize_text("2012年"), "二零一二年")
        self.assertEqual(normalize_text("28岁"), "二十八岁")
        self.assertEqual(normalize_text("15岁"), "十五岁")
        self.assertEqual(normalize_text("12~18岁"), "十二到十八岁")
        self.assertEqual(normalize_text("3.5%"), "百分之三点五")
        self.assertEqual(normalize_text("2012 年"), "二零一二年")
        self.assertEqual(normalize_text("28 岁"), "二十八岁")
        self.assertEqual(normalize_text("21 世纪"), "二十一世纪")

    def test_converts_large_numbers_without_failing(self) -> None:
        self.assertEqual(normalize_text("10000人"), "一万人")
        self.assertEqual(normalize_text("12000~15000人"), "一万二千到一万五千人")
        self.assertEqual(normalize_text("100000001人"), "一亿零一人")
        self.assertEqual(normalize_text("1000000000000岁"), "一零零零零零零零零零零零零岁")

    def test_preserves_word_spacing_and_paragraphs(self) -> None:
        text = "The service began in 2012年.\n\nHe was 28岁."

        self.assertEqual(normalize_text(text), "The service began in 二零一二年.\n\nHe was 二十八岁.")

    def test_preserves_heading_paragraph_breaks_but_removes_single_line_wraps(self) -> None:
        text = "（一）服务对象层面的目标\n\n一、缓解生活困难\n社会工作服务的目标。"

        self.assertEqual(
            normalize_text(text),
            "（一）服务对象层面的目标\n\n一、缓解生活困难社会工作服务的目标。",
        )

    def test_removes_quote_glyphs_and_markdown_bold_without_losing_words(self) -> None:
        extracted = '**“ ”\n社会建设是党中央 五位一体 总体布局的重要组成部分**'

        self.assertEqual(
            normalize_text(extracted),
            "社会建设是党中央五位一体总体布局的重要组成部分",
        )

    def test_removes_quote_styles_but_preserves_sentence_punctuation(self) -> None:
        text = "他说‘社会工作’很重要。《病理学》也会说：‘注意观察！’"

        self.assertEqual(normalize_text(text), "他说社会工作很重要。《病理学》也会说：注意观察！")

    def test_removes_quotes_split_across_extracted_lines(self) -> None:
        self.assertEqual(normalize_text("人民幸福安\n” “ ”康。"), "人民幸福安康。")


if __name__ == "__main__":
    unittest.main()