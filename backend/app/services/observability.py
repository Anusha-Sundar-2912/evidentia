import time
from dataclasses import dataclass, field


@dataclass
class RequestTimer:
    start_time: float = field(
        default_factory=time.perf_counter
    )

    stages: dict[str, float] = field(
        default_factory=dict
    )

    _stage_start: float | None = None
    _stage_name: str | None = None

    def start_stage(
        self,
        name: str,
    ) -> None:
        self._stage_name = name
        self._stage_start = time.perf_counter()

    def end_stage(self) -> None:
        if (
            self._stage_name is None
            or self._stage_start is None
        ):
            return

        elapsed = (
            time.perf_counter()
            - self._stage_start
        )

        self.stages[
            self._stage_name
        ] = round(
            elapsed * 1000,
            2,
        )

        self._stage_name = None
        self._stage_start = None

    def total_ms(self) -> float:
        return round(
            (
                time.perf_counter()
                - self.start_time
            )
            * 1000,
            2,
        )


def calculate_compression_metrics(
    original_results: list[dict],
    compressed_results: list[dict],
) -> dict:
    original_chars = sum(
        len(result.get("content", ""))
        for result in original_results
    )

    compressed_chars = sum(
        len(result.get("content", ""))
        for result in compressed_results
    )

    if original_chars == 0:
        compression_ratio = 1.0
    else:
        compression_ratio = (
            compressed_chars
            / original_chars
        )

    chars_saved = max(
        original_chars - compressed_chars,
        0,
    )

    return {
        "original_context_chars": original_chars,
        "compressed_context_chars": compressed_chars,
        "chars_saved": chars_saved,
        "compression_ratio": round(
            compression_ratio,
            4,
        ),
    }


def build_retrieval_trace(
    original_query: str,
    sanitized_query: str,
    rewritten_query: str,
    subqueries: list[str],
    results: list[dict],
    compressed_results: list[dict],
    stage_latency_ms: dict[str, float],
    total_latency_ms: float,
) -> dict:
    compression = calculate_compression_metrics(
        original_results=results,
        compressed_results=compressed_results,
    )

    selected_chunks = []

    for rank, result in enumerate(
        results,
        start=1,
    ):
        selected_chunks.append(
            {
                "rank": rank,
                "chunk_id": result["chunk_id"],
                "filename": result["filename"],
                "page_number": result.get(
                    "page_number"
                ),
                "reranker_score": result.get(
                    "reranker_score"
                ),
            }
        )

    return {
        "original_query": original_query,
        "sanitized_query": sanitized_query,
        "rewritten_query": rewritten_query,
        "subqueries": subqueries,
        "retrieved_chunk_count": len(results),
        "selected_chunks": selected_chunks,
        "compression": compression,
        "latency_ms": {
            **stage_latency_ms,
            "total": total_latency_ms,
        },
    }