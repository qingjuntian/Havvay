"""Convert the source DOCX into Chinese-TTS-friendly plain text."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "第一章社会工作服务的内涵.docx"
TARGET = ROOT / "data" / "book.txt"
DIGITS = "〇一二三四五六七八九"
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


def year_text(match: re.Match[str]) -> str:
    return "".join(DIGITS[int(digit)] for digit in match.group(1)) + "年"


def normalize(text: str) -> str:
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"^(\d+)\.(.+)$", lambda m: chinese_number(m.group(1)) + "、" + m.group(2), text)
    text = re.sub(r"(\d{4})年", year_text, text)
    text = re.sub(
        r"(\d+)\s*[~～至到]\s*(\d+)(岁|年|月|人|项|个)?",
        lambda m: chinese_number(m.group(1)) + "至" + chinese_number(m.group(2)) + (m.group(3) or ""),
        text,
    )
    text = re.sub(
        r"(\d+)\.(\d+)(岁|年|月|%|％)?",
        lambda m: chinese_number(m.group(1)) + "点" + "".join(SMALL_NUMBERS[int(d)] for d in m.group(2)) + (m.group(3) or ""),
        text,
    )
    text = re.sub(r"(\d+)世纪", lambda m: chinese_number(m.group(1)) + "世纪", text)
    text = re.sub(r"(\d+)岁", lambda m: chinese_number(m.group(1)) + "岁", text)
    return text


def extract_paragraphs() -> list[str]:
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with ZipFile(SOURCE) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    paragraphs = []
    for paragraph in root.findall(f".//{namespace}body/{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.findall(f".//{namespace}t"))
        if text.strip():
            paragraphs.append(normalize(text))
    return paragraphs


if __name__ == "__main__":
    paragraphs = extract_paragraphs()
    TARGET.write_text("\n\n".join(paragraphs) + "\n", encoding="utf-8")
    print(f"wrote {len(paragraphs)} paragraphs to {TARGET}")
