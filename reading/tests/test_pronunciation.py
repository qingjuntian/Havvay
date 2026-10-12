from __future__ import annotations

import unittest

from src.pronunciation import pypinyin_phrases, validate_pronunciation_entries


class PronunciationDictionaryTests(unittest.TestCase):
    def test_validates_and_normalizes_phrase_pronunciation(self) -> None:
        entries = validate_pronunciation_entries({" 单于 ": "SHAN4  yu2", "欧阳": "ou1 yang2"})

        self.assertEqual(entries, {"单于": "shan4 yu2", "欧阳": "ou1 yang2"})
        self.assertEqual(
            pypinyin_phrases(entries),
            {"单于": [["shan4"], ["yu2"]], "欧阳": [["ou1"], ["yang2"]]},
        )

    def test_rejects_wrong_syllable_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly 2"):
            validate_pronunciation_entries({"单于": "shan4"})

    def test_rejects_untoned_or_non_chinese_entries(self) -> None:
        with self.assertRaisesRegex(ValueError, "numbered pinyin"):
            validate_pronunciation_entries({"单于": "shan yu"})
        with self.assertRaisesRegex(ValueError, "Chinese characters"):
            validate_pronunciation_entries({"A于": "a1 yu2"})


if __name__ == "__main__":
    unittest.main()
