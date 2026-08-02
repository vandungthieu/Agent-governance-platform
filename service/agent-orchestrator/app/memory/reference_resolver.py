from __future__ import annotations

import re
import unicodedata


REFERENCE_PATTERNS = [
    r"khách hàng đó",
    r"khach hang do",
    r"khách hàng này",
    r"khach hang nay",
    r"khách này",
    r"khach nay",
    r"người đó",
    r"nguoi do",
    r"người này",
    r"nguoi nay",
    r"người ấy",
    r"nguoi ay",
    r"customer đó",
    r"customer do",
    r"customer này",
    r"customer nay",
]


def resolve_reference(input_text: str, memory_context: str) -> str:
    if not memory_context or not contains_reference(input_text):
        return input_text

    customer_name = latest_customer_name(memory_context)
    if not customer_name:
        return input_text

    resolved_text = input_text
    for pattern in REFERENCE_PATTERNS:
        resolved_text = re.sub(
            pattern,
            f"khách hàng {customer_name}",
            resolved_text,
            flags=re.IGNORECASE,
        )
    return resolved_text


def contains_reference(input_text: str) -> bool:
    normalized_input = normalize_text(input_text)
    return any(normalize_text(pattern) in normalized_input for pattern in REFERENCE_PATTERNS)


def latest_customer_name(memory_context: str) -> str | None:
    candidates: list[tuple[int, str]] = []
    patterns = [
        r"khách hàng\s+([A-ZÀ-Ỹ][\wÀ-ỹ'.-]*(?:\s+[A-ZÀ-Ỹ][\wÀ-ỹ'.-]*){1,5})",
        r"khach hang\s+([A-ZÀ-Ỹ][\wÀ-ỹ'.-]*(?:\s+[A-ZÀ-Ỹ][\wÀ-ỹ'.-]*){1,5})",
        r"customer\s+([A-ZÀ-Ỹ][\wÀ-ỹ'.-]*(?:\s+[A-ZÀ-Ỹ][\wÀ-ỹ'.-]*){1,5})",
        r"Họ và tên\s*\|\s*([^|\n]+)",
        r"Ho va ten\s*\|\s*([^|\n]+)",
        r"của khách hàng\s+([A-ZÀ-Ỹ][\wÀ-ỹ'.-]*(?:\s+[A-ZÀ-Ỹ][\wÀ-ỹ'.-]*){1,5})",
        r"cua khach hang\s+([A-ZÀ-Ỹ][\wÀ-ỹ'.-]*(?:\s+[A-ZÀ-Ỹ][\wÀ-ỹ'.-]*){1,5})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, memory_context, flags=re.IGNORECASE):
            name = clean_customer_name(match.group(1))
            if name:
                candidates.append((match.start(), name))

    if not candidates:
        return None

    return sorted(candidates, key=lambda item: item[0])[-1][1]


def clean_customer_name(value: str) -> str | None:
    cleaned = value.strip(" .,!?:;\"'`|")
    cleaned = re.sub(
        r"\s+(?:là|la|có|co|sinh|năm|nam|email|số|so|điện|dien|địa|dia|trạng|trang)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.strip(" .,!?:;\"'`|")
    if not cleaned or normalize_text(cleaned) in {"do", "nay", "ay", "duoc hoi"}:
        return None
    return cleaned


def normalize_text(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFD", value.lower())
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()
