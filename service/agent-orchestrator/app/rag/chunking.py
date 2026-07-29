def chunk_text(text: str, max_chars: int = 1200, overlap_chars: int = 150) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines())
    paragraphs = [part for part in normalized.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not current:
            current = paragraph
            continue

        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}"
            continue

        chunks.append(current)
        overlap = current[-overlap_chars:] if overlap_chars > 0 else ""
        current = f"{overlap}\n\n{paragraph}" if overlap else paragraph

    if current:
        chunks.append(current)

    return chunks or [text[:max_chars]]

