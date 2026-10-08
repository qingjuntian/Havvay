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

    def test_preserves_word_spacing_and_paragraphs(self) -> None:
        text = "The service began in 2012年.\n\nHe was 28岁."

        self.assertEqual(normalize_text(text), "The service began in 二零一二年.\n\nHe was 二十八岁.")


if __name__ == "__main__":
    unittest.main()