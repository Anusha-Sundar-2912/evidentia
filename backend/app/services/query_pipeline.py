from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.compressor import compress_results
from app.services.generator import (
    decompose_query,
    generate_answer,
    rewrite_query_with_history,
)
from app.services.guardrails import (
    evaluate_input,
    evaluate_output,
)
from app.services.memory import (
    create_conversation_id,
    get_history,
    save_turn,
)
from app.services.observability import (
    RequestTimer,
    build_retrieval_trace,
)
from app.services.rag import multi_query_search
from app.services.validation import validate_answer


def run_query_pipeline(
    db: Session,
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
    conversation_id: str | None = None,
) -> dict:
    """
    Execute Evidentia's complete production RAG pipeline.

    This function is shared by the public /ask endpoint
    and the evaluation system so benchmark runs exercise
    the same pipeline used by real queries.
    """

    timer = RequestTimer()

    # -----------------------------------------------------
    # 1. Input guardrails
    # -----------------------------------------------------

    timer.start_stage(
        "input_guardrails"
    )

    input_guardrail = evaluate_input(
        text=query,
        redact_sensitive_data=True,
    )

    timer.end_stage()

    if not input_guardrail.allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "The request was blocked by "
                    "Evidentia's input guardrails."
                ),
                "guardrails": {
                    "allowed": False,
                    "prompt_injection_detected": (
                        input_guardrail.prompt_injection_detected
                    ),
                    "pii_detected": (
                        input_guardrail.pii_detected
                    ),
                    "pii_types": (
                        input_guardrail.pii_types
                    ),
                    "reasons": (
                        input_guardrail.reasons
                    ),
                },
            },
        )

    sanitized_query = (
        input_guardrail.sanitized_text
    )

    # -----------------------------------------------------
    # 2. Conversation memory
    # -----------------------------------------------------

    active_conversation_id = (
        conversation_id
        or create_conversation_id()
    )

    timer.start_stage(
        "memory_lookup"
    )

    history = get_history(
        active_conversation_id
    )

    timer.end_stage()

    # -----------------------------------------------------
    # 3. Conversational query rewriting
    # -----------------------------------------------------

    timer.start_stage(
        "conversation_rewrite"
    )

    retrieval_query = rewrite_query_with_history(
        query=sanitized_query,
        history=history,
    )

    timer.end_stage()

    # -----------------------------------------------------
    # 4. Query decomposition
    # -----------------------------------------------------

    timer.start_stage(
        "query_decomposition"
    )

    subqueries = decompose_query(
        query=retrieval_query,
    )

    timer.end_stage()

    # -----------------------------------------------------
    # 5. Multi-query hybrid retrieval
    # -----------------------------------------------------

    retrieval_timings = {}

    timer.start_stage(
        "retrieval"
    )

    results = multi_query_search(
        db=db,
        original_query=retrieval_query,
        queries=subqueries,
        top_k=top_k,
        filters=filters,
        timings=retrieval_timings,
    )

    timer.end_stage()

    for stage_name, stage_time in (
        retrieval_timings.items()
    ):
        timer.stages[
            f"retrieval_{stage_name}"
        ] = stage_time

    # -----------------------------------------------------
    # 6. Contextual compression
    # -----------------------------------------------------

    timer.start_stage(
        "compression"
    )

    compressed_results = compress_results(
        query=retrieval_query,
        results=results,
        max_sentences=4,
    )

    timer.end_stage()

    # -----------------------------------------------------
    # 7. Grounded generation
    # -----------------------------------------------------

    timer.start_stage(
        "generation"
    )

    answer = generate_answer(
        query=retrieval_query,
        results=compressed_results,
    )

    timer.end_stage()

    # -----------------------------------------------------
    # 8. Citation + groundedness validation
    # -----------------------------------------------------

    timer.start_stage(
        "validation"
    )

    validation = validate_answer(
        answer=answer,
        results=results,
    )

    citations = [
        {
            "source_number": number,
            "filename": (
                results[number - 1]["filename"]
            ),
            "page_number": (
                results[number - 1]["page_number"]
            ),
            "chunk_id": (
                results[number - 1]["chunk_id"]
            ),
        }
        for number in validation[
            "citations_found"
        ]
        if 1 <= number <= len(results)
    ]

    timer.end_stage()

    # -----------------------------------------------------
    # 9. Output privacy guardrail
    # -----------------------------------------------------

    timer.start_stage(
        "output_guardrails"
    )

    output_guardrail = evaluate_output(
        answer
    )

    timer.end_stage()

    # -----------------------------------------------------
    # 10. Save conversation
    # -----------------------------------------------------

    timer.start_stage(
        "memory_save"
    )

    save_turn(
        conversation_id=active_conversation_id,
        user_message=sanitized_query,
        assistant_message=answer,
    )

    timer.end_stage()

    # -----------------------------------------------------
    # 11. Build observability trace
    # -----------------------------------------------------

    trace = build_retrieval_trace(
        # Never expose the raw pre-redaction query.
        original_query=sanitized_query,
        sanitized_query=sanitized_query,
        rewritten_query=retrieval_query,
        subqueries=subqueries,
        results=results,
        compressed_results=compressed_results,
        stage_latency_ms=timer.stages.copy(),
        total_latency_ms=timer.total_ms(),
    )

    # -----------------------------------------------------
    # 12. Structured pipeline result
    # -----------------------------------------------------

    return {
        "query": sanitized_query,
        "answer": answer,
        "citations": citations,
        "validation": validation,
        "guardrails": {
            "input": {
                "allowed": (
                    input_guardrail.allowed
                ),
                "prompt_injection_detected": (
                    input_guardrail.prompt_injection_detected
                ),
                "pii_detected": (
                    input_guardrail.pii_detected
                ),
                "pii_types": (
                    input_guardrail.pii_types
                ),
                "pii_redacted": (
                    input_guardrail.sanitized_text
                    != input_guardrail.original_text
                ),
                "reasons": (
                    input_guardrail.reasons
                ),
            },
            "output": {
                "safe": (
                    output_guardrail["safe"]
                ),
                "pii_detected": (
                    output_guardrail[
                        "pii_detected"
                    ]
                ),
                "pii_types": (
                    output_guardrail[
                        "pii_types"
                    ]
                ),
            },
        },
        "trace": trace,
        "conversation_id": (
            active_conversation_id
        ),

        # Internal fields used by evaluation.
        # The public AskResponse schema ignores these.
        "_evaluation": {
            "retrieved_results": results,
            "compressed_results": (
                compressed_results
            ),
        },
    }