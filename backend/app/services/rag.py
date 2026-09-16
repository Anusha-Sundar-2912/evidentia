import re
import time

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document
from app.services.embeddings import generate_embedding
from app.services.reranker import rerank_results


def tokenize(text: str) -> list[str]:
    return re.findall(
        r"\b\w+\b",
        text.lower(),
    )


def elapsed_ms(start_time: float) -> float:
    return round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )


def apply_filters(
    statement,
    filters: dict | None,
):
    """
    Apply metadata filters at the database-query level
    before retrieval/ranking.
    """

    if not filters:
        return statement

    filenames = filters.get("filenames")
    source_types = filters.get("source_types")
    page_numbers = filters.get("page_numbers")

    if filenames:
        statement = statement.where(
            Document.filename.in_(filenames)
        )

    if source_types:
        statement = statement.where(
            Document.source_type.in_(source_types)
        )

    if page_numbers:
        statement = statement.where(
            Chunk.page_number.in_(page_numbers)
        )

    return statement


def semantic_search(
    db: Session,
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> list[dict]:
    query_embedding = generate_embedding(query)

    distance = Chunk.embedding.cosine_distance(
        query_embedding
    )

    statement = (
        select(
            Chunk,
            Document.filename,
            distance.label("distance"),
        )
        .join(
            Document,
            Chunk.document_id == Document.id,
        )
        .where(
            Chunk.embedding.is_not(None)
        )
    )

    statement = apply_filters(
        statement,
        filters,
    )

    statement = (
        statement
        .order_by(distance)
        .limit(top_k)
    )

    rows = db.execute(statement).all()

    results = []

    for chunk, filename, cosine_distance in rows:
        similarity_score = (
            1 - float(cosine_distance)
        )

        results.append(
            {
                "chunk_id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "filename": filename,
                "score": round(
                    similarity_score,
                    4,
                ),
            }
        )

    return results


def bm25_search(
    db: Session,
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> list[dict]:
    statement = (
        select(
            Chunk,
            Document.filename,
        )
        .join(
            Document,
            Chunk.document_id == Document.id,
        )
    )

    statement = apply_filters(
        statement,
        filters,
    )

    rows = db.execute(statement).all()

    if not rows:
        return []

    corpus = [
        tokenize(chunk.content)
        for chunk, _ in rows
    ]

    bm25 = BM25Okapi(corpus)

    query_tokens = tokenize(query)

    scores = bm25.get_scores(
        query_tokens
    )

    ranked = sorted(
        zip(rows, scores),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]

    results = []

    for (chunk, filename), score in ranked:
        results.append(
            {
                "chunk_id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "filename": filename,
                "score": round(
                    float(score),
                    4,
                ),
            }
        )

    return results


def reciprocal_rank_fusion(
    semantic_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    fused_scores = {}
    chunk_map = {}

    for rank, result in enumerate(
        semantic_results,
        start=1,
    ):
        chunk_id = result["chunk_id"]

        fused_scores[chunk_id] = (
            fused_scores.get(
                chunk_id,
                0.0,
            )
            + 1 / (k + rank)
        )

        chunk_map[chunk_id] = result

    for rank, result in enumerate(
        bm25_results,
        start=1,
    ):
        chunk_id = result["chunk_id"]

        fused_scores[chunk_id] = (
            fused_scores.get(
                chunk_id,
                0.0,
            )
            + 1 / (k + rank)
        )

        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = result

    ranked_ids = sorted(
        fused_scores,
        key=fused_scores.get,
        reverse=True,
    )

    results = []

    for chunk_id in ranked_ids:
        result = chunk_map[
            chunk_id
        ].copy()

        result["score"] = round(
            fused_scores[chunk_id],
            6,
        )

        results.append(result)

    return results


def hybrid_candidates(
    db: Session,
    query: str,
    top_k: int = 10,
    filters: dict | None = None,
    timings: dict | None = None,
) -> list[dict]:
    semantic_start = time.perf_counter()

    semantic_results = semantic_search(
        db=db,
        query=query,
        top_k=top_k,
        filters=filters,
    )

    semantic_time = elapsed_ms(
        semantic_start
    )

    bm25_start = time.perf_counter()

    bm25_results = bm25_search(
        db=db,
        query=query,
        top_k=top_k,
        filters=filters,
    )

    bm25_time = elapsed_ms(
        bm25_start
    )

    rrf_start = time.perf_counter()

    fused_results = reciprocal_rank_fusion(
        semantic_results=semantic_results,
        bm25_results=bm25_results,
    )

    rrf_time = elapsed_ms(
        rrf_start
    )

    if timings is not None:
        timings["semantic_search"] = round(
            timings.get(
                "semantic_search",
                0.0,
            )
            + semantic_time,
            2,
        )

        timings["bm25_search"] = round(
            timings.get(
                "bm25_search",
                0.0,
            )
            + bm25_time,
            2,
        )

        timings["rrf"] = round(
            timings.get(
                "rrf",
                0.0,
            )
            + rrf_time,
            2,
        )

    return fused_results


def hybrid_search(
    db: Session,
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
) -> list[dict]:
    candidate_count = max(
        top_k * 3,
        10,
    )

    fused_results = hybrid_candidates(
        db=db,
        query=query,
        top_k=candidate_count,
        filters=filters,
    )

    reranked_results = rerank_results(
        query=query,
        results=fused_results,
        top_k=top_k,
    )

    return reranked_results


def merge_multi_query_results(
    result_sets: list[list[dict]],
) -> list[dict]:
    merged = {}

    for results in result_sets:
        for result in results:
            chunk_id = result["chunk_id"]

            if chunk_id not in merged:
                merged[chunk_id] = result.copy()

                merged[chunk_id][
                    "multi_query_score"
                ] = result.get(
                    "score",
                    0.0,
                )

                merged[chunk_id][
                    "query_hits"
                ] = 1

            else:
                merged[chunk_id][
                    "multi_query_score"
                ] += result.get(
                    "score",
                    0.0,
                )

                merged[chunk_id][
                    "query_hits"
                ] += 1

    results = list(
        merged.values()
    )

    results.sort(
        key=lambda item: (
            item["query_hits"],
            item["multi_query_score"],
        ),
        reverse=True,
    )

    return results


def multi_query_search(
    db: Session,
    original_query: str,
    queries: list[str],
    top_k: int = 5,
    filters: dict | None = None,
    timings: dict | None = None,
) -> list[dict]:
    """
    Multi-query retrieval with intent coverage,
    metadata filtering, and detailed retrieval timing.

    The timing dictionary is optional so existing
    callers remain compatible.
    """

    clean_queries = list(
        dict.fromkeys(
            query.strip()
            for query in queries
            if query.strip()
        )
    )

    if not clean_queries:
        clean_queries = [
            original_query
        ]

    candidate_count = max(
        top_k * 3,
        10,
    )

    retrieval_timings = {
        "semantic_search": 0.0,
        "bm25_search": 0.0,
        "rrf": 0.0,
        "focused_reranking": 0.0,
        "global_reranking": 0.0,
    }

    result_sets = []

    for query in clean_queries:
        candidates = hybrid_candidates(
            db=db,
            query=query,
            top_k=candidate_count,
            filters=filters,
            timings=retrieval_timings,
        )

        rerank_start = time.perf_counter()

        focused_results = rerank_results(
            query=query,
            results=candidates,
            top_k=max(
                top_k,
                5,
            ),
        )

        retrieval_timings[
            "focused_reranking"
        ] = round(
            retrieval_timings[
                "focused_reranking"
            ]
            + elapsed_ms(rerank_start),
            2,
        )

        result_sets.append(
            focused_results
        )

    selected = []
    selected_ids = set()

    # Coverage pass:
    # preserve the strongest candidate from
    # each decomposed information need.
    for results in result_sets:
        if not results:
            continue

        best_result = results[0]

        chunk_id = best_result[
            "chunk_id"
        ]

        if chunk_id not in selected_ids:
            selected.append(
                best_result
            )

            selected_ids.add(
                chunk_id
            )

        if len(selected) >= top_k:
            break

    candidate_pool = []

    for results in result_sets:
        for result in results:
            chunk_id = result[
                "chunk_id"
            ]

            if chunk_id in selected_ids:
                continue

            candidate_pool.append(
                result
            )

    deduplicated_pool = []
    pool_ids = set()

    for result in candidate_pool:
        chunk_id = result[
            "chunk_id"
        ]

        if chunk_id in pool_ids:
            continue

        deduplicated_pool.append(
            result
        )

        pool_ids.add(
            chunk_id
        )

    remaining_slots = max(
        top_k - len(selected),
        0,
    )

    if (
        remaining_slots > 0
        and deduplicated_pool
    ):
        global_rerank_start = (
            time.perf_counter()
        )

        globally_reranked = rerank_results(
            query=original_query,
            results=deduplicated_pool,
            top_k=remaining_slots,
        )

        retrieval_timings[
            "global_reranking"
        ] = round(
            retrieval_timings[
                "global_reranking"
            ]
            + elapsed_ms(
                global_rerank_start
            ),
            2,
        )

        for result in globally_reranked:
            chunk_id = result[
                "chunk_id"
            ]

            if chunk_id in selected_ids:
                continue

            selected.append(
                result
            )

            selected_ids.add(
                chunk_id
            )

    if timings is not None:
        timings.update(
            retrieval_timings
        )

    return selected[:top_k]