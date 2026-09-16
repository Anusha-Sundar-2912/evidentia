from sentence_transformers import CrossEncoder


_reranker = None


def get_reranker():
    global _reranker

    if _reranker is None:
        _reranker = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

    return _reranker


def rerank_results(
    query: str,
    results: list[dict],
    top_k: int = 5,
) -> list[dict]:
    if not results:
        return []

    model = get_reranker()

    pairs = [
        [
            query,
            result["content"],
        ]
        for result in results
    ]

    scores = model.predict(
        pairs
    )

    reranked = []

    for result, score in zip(
        results,
        scores,
    ):
        item = result.copy()

        item["reranker_score"] = round(
            float(score),
            4,
        )

        reranked.append(item)

    reranked.sort(
        key=lambda item: item[
            "reranker_score"
        ],
        reverse=True,
    )

    return reranked[:top_k]