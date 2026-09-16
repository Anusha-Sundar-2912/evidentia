import re

import numpy as np

from app.services.embeddings import get_embedding_model


def split_sentences(text: str) -> list[str]:
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

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


def compress_text(
    query: str,
    text: str,
    max_sentences: int = 4,
    similarity_threshold: float = 0.20,
) -> str:
    """
    Select the sentences from a retrieved chunk
    that are most semantically relevant to the query.
    """

    sentences = split_sentences(text)

    if not sentences:
        return text

    if len(sentences) <= max_sentences:
        return text

    model = get_embedding_model()

    embeddings = model.encode(
        [query, *sentences],
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    query_embedding = embeddings[0]
    sentence_embeddings = embeddings[1:]

    similarities = np.dot(
        sentence_embeddings,
        query_embedding,
    )

    ranked_indices = np.argsort(
        similarities
    )[::-1]

    selected_indices = []

    for index in ranked_indices:
        if (
            float(similarities[index])
            >= similarity_threshold
        ):
            selected_indices.append(
                int(index)
            )

        if len(selected_indices) >= max_sentences:
            break

    # If the threshold removes everything,
    # preserve the single strongest sentence.
    if not selected_indices:
        selected_indices = [
            int(ranked_indices[0])
        ]

    # Restore original document order rather than
    # similarity-score order.
    selected_indices.sort()

    return " ".join(
        sentences[index]
        for index in selected_indices
    )


def compress_results(
    query: str,
    results: list[dict],
    max_sentences: int = 4,
) -> list[dict]:
    """
    Compress retrieved chunks while preserving their
    source metadata and original content.
    """

    compressed_results = []

    for result in results:
        item = result.copy()

        original_content = result[
            "content"
        ]

        compressed_content = compress_text(
            query=query,
            text=original_content,
            max_sentences=max_sentences,
        )

        item["original_content"] = (
            original_content
        )

        item["content"] = (
            compressed_content
        )

        item["original_length"] = len(
            original_content
        )

        item["compressed_length"] = len(
            compressed_content
        )

        compressed_results.append(
            item
        )

    return compressed_results