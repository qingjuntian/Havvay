"""Normalize Chinese book text for TTS and page matching."""

from __future__ import annotations

import re

DIGITS = "零一二三四五六七八九"
SMALL_NUMBERS = "零一二三四五六七八九"


def chinese_number(value: str) -> str:
    number = int(value)
    if number < 0:
        raise ValueError("chinese_number expects a non-negative integer")
    if number < 10:
        return SMALL_NUMBERS[number]
    if number < 20:
        return "十" + (SMALL_NUMBERS[number % 10] if number > 10 else "")
    if number < 10000:
        result = ""
        zero_pending = False
        for divisor, unit in ((1000, "千"), (100, "百"), (10, "十"), (1, "")):
            digit, number = divmod(number, divisor)
            if digit:
                if zero_pending:
                    result += "零"
                    zero_pending = False
                result += SMALL_NUMBERS[digit] + unit
            elif result and number:
                zero_pending = True
        return result

    if number < 100_000_000:
        high, low = divmod(number, 10_000)
        result = chinese_number(str(high)) + "万"
        if low:
            if low < 1000:
                result += "零"
            result += chinese_number(str(low))
        return result

    if number < 1_000_000_000_000:
        high, low = divmod(number, 100_000_000)
        result = chinese_number(str(high)) + "亿"
        if low:
            if low < 10_000_000:
                result += "零"
            result += chinese_number(str(low))
        return result

    return "".join(DIGITS[int(digit)] for digit in str(number))


def _year(match: re.Match[str]) -> str:
    return "".join(DIGITS[int(digit)] for digit in match.group(1)) + "年"


def normalize_text(text: str) -> str:
    """Make text readable by Chinese TTS while retaining useful punctuation."""
    text = text.replace("**", "")
    text = re.sub(r"[\"'“”‘’「」『』《》〈〉]", "", text)
    text = text.replace("％", "%")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\r?\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = re.sub(r"(\d{4})\s*年", _year, text)
    text = re.sub(
        r"(\d+)\s*[~～至到]\s*(\d+)\s*(岁|年|月|人|项|个)?",
        lambda m: chinese_number(m.group(1)) + "到" + chinese_number(m.group(2)) + (m.group(3) or ""),
        text,
    )
    text = re.sub(
        r"(\d+)\.(\d+)\s*(岁|年|月|%)?",
        lambda m: ("百分之" if m.group(3) == "%" else "") + chinese_number(m.group(1)) + "点" + "".join(SMALL_NUMBERS[int(d)] for d in m.group(2)) + ("" if m.group(3) == "%" else (m.group(3) or "")),
        text,
    )
    text = re.sub(r"^(\d+)\.\s*(?=[^\d])", lambda m: chinese_number(m.group(1)) + "、", text)
    text = re.sub(r"(\d+)\s*%", lambda m: "百分之" + chinese_number(m.group(1)), text)
    text = re.sub(r"(\d+)\s*世纪", lambda m: chinese_number(m.group(1)) + "世纪", text)
    text = re.sub(
        r"(\d+)\s*(岁|年|月|人|项|个)",
        lambda m: chinese_number(m.group(1)) + m.group(2),
        text,
    )
    text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    return text


def match_text(text: str) -> str:
    """Normalize text for PDF/chunk alignment, ignoring punctuation differences."""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", normalize_text(text)).lower()
