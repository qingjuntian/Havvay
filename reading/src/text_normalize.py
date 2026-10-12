"""Normalize Chinese book text for TTS and page matching."""

from __future__ import annotations

import re

DIGITS = "零一二三四五六七八九"
SMALL_NUMBERS = "零一二三四五六七八九"


def chinese_number(value: str) -> str:
    number = int(value)
    if number < 10:
        return SMALL_NUMBERS[number]
    if number < 20:
        return "十" if number == 10 else "十" + SMALL_NUMBERS[number % 10]
    if number < 100:
        tens, ones = divmod(number, 10)
        return SMALL_NUMBERS[tens] + "十" + (SMALL_NUMBERS[ones] if ones else "")
    if number < 1000:
        hundreds, remainder = divmod(number, 100)
        if remainder == 0:
            return SMALL_NUMBERS[hundreds] + "百"
        if remainder < 10:
            return SMALL_NUMBERS[hundreds] + "百零" + SMALL_NUMBERS[remainder]
        return SMALL_NUMBERS[hundreds] + "百" + chinese_number(str(remainder))
    if number < 10000:
        thousands, remainder = divmod(number, 1000)
        if remainder == 0:
            return SMALL_NUMBERS[thousands] + "千"
        if remainder < 100:
            return SMALL_NUMBERS[thousands] + "千零" + chinese_number(str(remainder))
        return SMALL_NUMBERS[thousands] + "千" + chinese_number(str(remainder))
    raise ValueError(f"number too large for this converter: {value}")


def _year(match: re.Match[str]) -> str:
    return "".join(DIGITS[int(digit)] for digit in match.group(1)) + "年"


def normalize_text(text: str) -> str:
    """Make text readable by Chinese TTS while retaining useful punctuation."""
    text = text.replace("％", "%")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"(\d{4})年", _year, text)
    text = re.sub(
        r"(\d+)\s*[~～至到]\s*(\d+)(岁|年|月|人|项|个)?",
        lambda m: chinese_number(m.group(1)) + "到" + chinese_number(m.group(2)) + (m.group(3) or ""),
        text,
    )
    text = re.sub(
        r"(\d+)\.(\d+)(岁|年|月|%)?",
        lambda m: ("百分之" if m.group(3) == "%" else "") + chinese_number(m.group(1)) + "点" + "".join(SMALL_NUMBERS[int(d)] for d in m.group(2)) + ("" if m.group(3) == "%" else (m.group(3) or "")),
        text,
    )
    text = re.sub(r"^(\d+)\.\s*(?=[^\d])", lambda m: chinese_number(m.group(1)) + "、", text)
    text = re.sub(r"(\d+)%", lambda m: "百分之" + chinese_number(m.group(1)), text)
    text = re.sub(r"(\d+)世纪", lambda m: chinese_number(m.group(1)) + "世纪", text)
    text = re.sub(r"(\d+)岁", lambda m: chinese_number(m.group(1)) + "岁", text)
    return text


def match_text(text: str) -> str:
    """Normalize text for PDF/chunk alignment, ignoring punctuation differences."""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", normalize_text(text)).lower()
