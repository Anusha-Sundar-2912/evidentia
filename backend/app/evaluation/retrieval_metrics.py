import math


def get_retrieved_chunk_ids(
    results: list[dict],
) -> list[str]:
    return [
        str(result["chunk_id"])
        for result in results
    ]


def hit_rate_at_k(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int,
) -> float:
    if not relevant_ids:
        return 0.0

    return float(
        bool(
            set(retrieved_ids[:k])
            & set(relevant_ids)
        )
    )


def precision_at_k(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int,
) -> float:
    if k <= 0:
        return 0.0

    top_k = retrieved_ids[:k]

    if not top_k:
        return 0.0

    relevant = set(
        relevant_ids
    )

    hits = sum(
        1
        for chunk_id in top_k
        if chunk_id in relevant
    )

    return round(
        hits / len(top_k),
        4,
    )


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int,
) -> float:
    if not relevant_ids:
        return 0.0

    relevant = set(
        relevant_ids
    )

    retrieved = set(
        retrieved_ids[:k]
    )

    return round(
        len(retrieved & relevant)
        / len(relevant),
        4,
    )


def reciprocal_rank(
    retrieved_ids: list[str],
    relevant_ids: list[str],
) -> float:
    relevant = set(
        relevant_ids
    )

    for rank, chunk_id in enumerate(
        retrieved_ids,
        start=1,
    ):
        if chunk_id in relevant:
            return round(
                1.0 / rank,
                4,
            )

    return 0.0


def graded_ndcg_at_k(
    retrieved_ids: list[str],
    relevance_judgments: dict[str, float],
    k: int,
) -> float:
    """
    Graded nDCG using gain = 2^relevance - 1.

    This rewards placing strongly relevant chunks
    above partially relevant chunks.
    """

    if (
        not retrieved_ids
        or not relevance_judgments
        or k <= 0
    ):
        return 0.0

    dcg = 0.0

    for rank, chunk_id in enumerate(
        retrieved_ids[:k],
        start=1,
    ):
        relevance = float(
            relevance_judgments.get(
                chunk_id,
                0.0,
            )
        )

        gain = (
            (2 ** relevance)
            - 1
        )

        dcg += (
            gain
            / math.log2(rank + 1)
        )

    ideal_relevances = sorted(
        relevance_judgments.values(),
        reverse=True,
    )[:k]

    idcg = 0.0

    for rank, relevance in enumerate(
        ideal_relevances,
        start=1,
    ):
        gain = (
            (2 ** float(relevance))
            - 1
        )

        idcg += (
            gain
            / math.log2(rank + 1)
        )

    if idcg == 0:
        return 0.0

    return round(
        dcg / idcg,
        4,
    )


def calculate_retrieval_metrics(
    results: list[dict],
    relevant_chunk_ids: list[str],
    relevance_judgments: (
        dict[str, float] | None
    ) = None,
    k: int = 5,
) -> dict:
    retrieved_ids = (
        get_retrieved_chunk_ids(
            results
        )
    )

    judgments = (
        relevance_judgments
        or {
            chunk_id: 1.0
            for chunk_id
            in relevant_chunk_ids
        }
    )

    return {
        "hit_rate_at_k": hit_rate_at_k(
            retrieved_ids,
            relevant_chunk_ids,
            k,
        ),
        "precision_at_k": precision_at_k(
            retrieved_ids,
            relevant_chunk_ids,
            k,
        ),
        "recall_at_k": recall_at_k(
            retrieved_ids,
            relevant_chunk_ids,
            k,
        ),
        "reciprocal_rank": reciprocal_rank(
            retrieved_ids,
            relevant_chunk_ids,
        ),
        "ndcg_at_k": graded_ndcg_at_k(
            retrieved_ids,
            judgments,
            k,
        ),
    }