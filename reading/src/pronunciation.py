"""Validation helpers for per-book Chinese pronunciation dictionaries."""

from __future__ import annotations

import json
import re
from pathlib import Path

_HAN_RE = re.compile(r"^[\u3400-\u9fff]+$")
_PINYIN_SYLLABLE_RE = re.compile(r"^[a-zvü]+[1-5]$")


def validate_pronunciation_entries(entries: dict[str, str]) -> dict[str, str]:
    """Validate phrase-to-tone-number-pinyin entries and return normalized values."""
    if not isinstance(entries, dict):
        raise ValueError("Pronunciation dictionary must be a JSON object")

    normalized: dict[str, str] = {}
    for phrase, pronunciation in entries.items():
        if not isinstance(phrase, str) or not isinstance(pronunciation, str):
            raise ValueError("Each dictionary entry must map a Chinese phrase to pinyin text")
        phrase = phrase.strip()
        pronunciation = pronunciation.strip().lower()
        if not 1 <= len(phrase) <= 12 or not _HAN_RE.fullmatch(phrase):
            raise ValueError(f"Dictionary key must contain 1 to 12 Chinese characters: {phrase!r}")
        syllables = pronunciation.split()
        if len(syllables) != len(phrase):
            raise ValueError(f"{phrase!r} needs exactly {len(phrase)} pinyin syllables")
        if any(not _PINYIN_SYLLABLE_RE.fullmatch(syllable) for syllable in syllables):
            raise ValueError(f"Use numbered pinyin syllables such as 'chong2 yang2' for {phrase!r}")
        if phrase in normalized:
            raise ValueError(f"Duplicate dictionary phrase: {phrase!r}")
        normalized[phrase] = " ".join(syllables)
    return normalized


def pypinyin_phrases(entries: dict[str, str]) -> dict[str, list[list[str]]]:
    """Convert numbered-pinyin strings to pypinyin's tone2 phrase-dictionary shape."""
    checked = validate_pronunciation_entries(entries)
    return {
        phrase: [[syllable] for syllable in pronunciation.split()]
        for phrase, pronunciation in checked.items()
    }


def read_pronunciation_file(path: Path) -> dict[str, str]:
    """Read and validate a JSON pronunciation dictionary."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Pronunciation dictionary must be a JSON object")
    return validate_pronunciation_entries(payload)
