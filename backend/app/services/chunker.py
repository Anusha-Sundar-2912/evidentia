import re


def split_into_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text,
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[str]:
    sentences = split_into_sentences(text)

    if not sentences:
        return []

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        candidate = (
            f"{current_chunk} {sentence}".strip()
            if current_chunk
            else sentence
        )

        if len(candidate) <= chunk_size:
            current_chunk = candidate
            continue

        if current_chunk:
            chunks.append(current_chunk)

        if overlap > 0 and chunks:
            overlap_text = chunks[-1][-overlap:]
            current_chunk = (
                f"{overlap_text} {sentence}".strip()
            )
        else:
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[dict]:
    all_chunks = []
    chunk_index = 0

    for page in pages:
        text = page["text"]
        page_number = page.get("page_number")

        chunks = chunk_text(
            text,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk in chunks:
            all_chunks.append(
                {
                    "chunk_index": chunk_index,
                    "content": chunk,
                    "page_number": page_number,
                }
            )

            chunk_index += 1

    return all_chunks