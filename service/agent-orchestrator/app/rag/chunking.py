import re


def split_long_text(text: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?。！？])\s+", text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                sentence[index : index + max_chars]
                for index in range(0, len(sentence), max_chars)
            )
            continue
        if not current:
            current = sentence
            continue
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}"
            continue
        chunks.append(current)
        current = sentence

    if current:
        chunks.append(current)

    return chunks


def chunk_text(text: str, max_chars: int = 1200, overlap_chars: int = 150) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be greater than or equal to 0")
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be smaller than max_chars")

    normalized = "\n".join(line.strip() for line in text.splitlines())
    paragraphs = [part for part in normalized.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs or [normalized]:
        paragraph = paragraph.strip()
        paragraph_parts = split_long_text(paragraph, max_chars)

        for paragraph_part in paragraph_parts:
            current = add_part_to_chunks(
                chunks=chunks,
                current=current,
                part=paragraph_part,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
            )

    if current:
        chunks.append(current)

    return chunks or [text[:max_chars]]


def add_part_to_chunks(
    chunks: list[str],
    current: str,
    part: str,
    max_chars: int,
    overlap_chars: int,
) -> str:
    if not part:
        return current

    if not current:
        return part

    if len(current) + len(part) + 2 <= max_chars:
        return f"{current}\n\n{part}"

    chunks.append(current)
    overlap = current[-overlap_chars:] if overlap_chars > 0 else ""
    next_chunk = f"{overlap}\n\n{part}" if overlap else part
    if len(next_chunk) <= max_chars:
        return next_chunk

    return part
