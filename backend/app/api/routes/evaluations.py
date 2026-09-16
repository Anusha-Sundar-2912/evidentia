import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.evaluation.benchmark import EVALUATION_CASES
from app.evaluation.claim_evaluator import (
    evaluate_claim_grounding,
)
from app.evaluation.dataset_generator import (
    discover_relevance_candidates,
    generate_evaluation_dataset,
)
from app.evaluation.relevance_judge import (
    get_positive_chunk_ids,
    judge_candidate_relevance,
    summarize_relevance_judgments,
)
from app.evaluation.retrieval_metrics import (
    calculate_retrieval_metrics,
)
from app.services.evaluation import evaluate_case
from app.services.query_pipeline import run_query_pipeline


router = APIRouter()


# =========================================================
# CONFIGURATION
# =========================================================


ALLOWED_DIFFICULTIES = {
    "direct",
    "paraphrase",
    "deep_retrieval",
}

RELEVANCE_THRESHOLD = 2.0
RELEVANCE_CANDIDATE_COUNT = 20


# =========================================================
# SHARED VALIDATION
# =========================================================


def validate_generation_parameters(
    sample_size: int,
    difficulty: str,
) -> None:
    if sample_size < 1 or sample_size > 25:
        raise HTTPException(
            status_code=400,
            detail=(
                "sample_size must be between "
                "1 and 25."
            ),
        )

    if difficulty not in ALLOWED_DIFFICULTIES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Unsupported evaluation "
                    "difficulty."
                ),
                "allowed": sorted(
                    ALLOWED_DIFFICULTIES
                ),
            },
        )


# =========================================================
# GENERATED DATASET
# =========================================================


@router.post("/generate")
def generate_dataset(
    sample_size: int = 5,
    difficulty: str = "paraphrase",
    db: Session = Depends(get_db),
):
    """
    Generate fresh evidence-grounded evaluation cases
    from Evidentia's currently ingested knowledge base.
    """

    validate_generation_parameters(
        sample_size=sample_size,
        difficulty=difficulty,
    )

    cases = generate_evaluation_dataset(
        db=db,
        sample_size=sample_size,
        difficulty=difficulty,
    )

    return {
        "requested_cases": sample_size,
        "generated_cases": len(cases),
        "difficulty": difficulty,
        "complete": (
            len(cases)
            == sample_size
        ),
        "cases": cases,
    }


# =========================================================
# GENERATED EVALUATION
# =========================================================


@router.post("/run-generated")
def run_generated_evaluations(
    sample_size: int = 5,
    difficulty: str = "paraphrase",
    top_k: int = 5,
    db: Session = Depends(get_db),
):
    """
    Generate unseen KB-specific evaluation cases and
    execute them through Evidentia's real production
    query pipeline.

    Evaluation includes:

    - multi-positive graded relevance judgment
    - Hit@K
    - Precision@K
    - Recall@K
    - MRR
    - graded nDCG@K
    - semantic claim-level faithfulness
    - citation correctness
    - citation coverage
    - production validator status
    - latency
    """

    validate_generation_parameters(
        sample_size=sample_size,
        difficulty=difficulty,
    )

    if top_k < 1 or top_k > 20:
        raise HTTPException(
            status_code=400,
            detail=(
                "top_k must be between "
                "1 and 20."
            ),
        )

    generated_cases = (
        generate_evaluation_dataset(
            db=db,
            sample_size=sample_size,
            difficulty=difficulty,
        )
    )

    evaluation_results = []

    total_latency = 0.0

    for case in generated_cases:
        start_time = time.perf_counter()

        # =================================================
        # 1. BUILD RELEVANCE-JUDGMENT CANDIDATE POOL
        # =================================================

        relevance_candidates = (
            discover_relevance_candidates(
                db=db,
                question=case["question"],
                source_chunk_ids=case[
                    "source_chunk_ids"
                ],
                candidate_count=(
                    RELEVANCE_CANDIDATE_COUNT
                ),
            )
        )

        # =================================================
        # 2. GRADED RELEVANCE JUDGMENT
        # =================================================

        relevance_judgments = (
            judge_candidate_relevance(
                question=case["question"],
                reference_answer=case[
                    "reference_answer"
                ],
                candidates=(
                    relevance_candidates
                ),
                guaranteed_chunk_ids=case[
                    "source_chunk_ids"
                ],
            )
        )

        relevant_chunk_ids = (
            get_positive_chunk_ids(
                judgments=(
                    relevance_judgments
                ),
                minimum_relevance=(
                    RELEVANCE_THRESHOLD
                ),
            )
        )

        relevance_diagnostics = (
            summarize_relevance_judgments(
                relevance_judgments
            )
        )

        # =================================================
        # 3. RUN REAL PRODUCTION QUERY PIPELINE
        # =================================================

        pipeline_result = (
            run_query_pipeline(
                db=db,
                query=case["question"],
                top_k=top_k,
            )
        )

        retrieved_results = (
            pipeline_result[
                "_evaluation"
            ][
                "retrieved_results"
            ]
        )

        # =================================================
        # 4. RETRIEVAL METRICS
        # =================================================

        retrieval_metrics = (
            calculate_retrieval_metrics(
                results=(
                    retrieved_results
                ),
                relevant_chunk_ids=(
                    relevant_chunk_ids
                ),
                relevance_judgments=(
                    relevance_judgments
                ),
                k=top_k,
            )
        )

        # =================================================
        # 5. SEMANTIC CLAIM-LEVEL EVALUATION
        # =================================================

        semantic_evaluation = (
            evaluate_claim_grounding(
                answer=pipeline_result[
                    "answer"
                ],
                results=(
                    retrieved_results
                ),
            )
        )

        # =================================================
        # 6. LATENCY
        # =================================================

        latency_ms = round(
            (
                time.perf_counter()
                - start_time
            )
            * 1000,
            2,
        )

        total_latency += latency_ms

        # =================================================
        # 7. CASE REPORT
        # =================================================

        evaluation_results.append(
            {
                "case_id": case["id"],
                "difficulty": case[
                    "difficulty"
                ],
                "evaluation_type": case[
                    "evaluation_type"
                ],
                "question": case[
                    "question"
                ],
                "reference_answer": case[
                    "reference_answer"
                ],
                "answer": pipeline_result[
                    "answer"
                ],
                "ground_truth": {
                    "originating_document": (
                        case[
                            "source_document"
                        ]
                    ),
                    "originating_pages": (
                        case[
                            "source_pages"
                        ]
                    ),
                    "originating_chunk_ids": (
                        case[
                            "source_chunk_ids"
                        ]
                    ),
                    "relevant_chunk_ids": (
                        relevant_chunk_ids
                    ),
                    "relevance_judgments": (
                        relevance_judgments
                    ),
                    "relevance_diagnostics": (
                        relevance_diagnostics
                    ),
                },
                "retrieval": (
                    retrieval_metrics
                ),
                "semantic_evaluation": (
                    semantic_evaluation
                ),
                "production_validation": (
                    pipeline_result[
                        "validation"
                    ]
                ),
                "citations": pipeline_result[
                    "citations"
                ],
                "latency_ms": latency_ms,
            }
        )

    # =====================================================
    # AGGREGATION
    # =====================================================

    total_cases = len(
        evaluation_results
    )

    def average_nested_metric(
        section: str,
        metric: str,
    ) -> float:
        if total_cases == 0:
            return 0.0

        return round(
            sum(
                float(
                    result[
                        section
                    ][
                        metric
                    ]
                )
                for result
                in evaluation_results
            )
            / total_cases,
            4,
        )

    successful_retrievals = sum(
        1
        for result
        in evaluation_results
        if result[
            "retrieval"
        ][
            "hit_rate_at_k"
        ] == 1.0
    )

    production_valid_answers = sum(
        1
        for result
        in evaluation_results
        if result[
            "production_validation"
        ].get(
            "valid",
            False,
        )
    )

    fully_faithful_answers = sum(
        1
        for result
        in evaluation_results
        if result[
            "semantic_evaluation"
        ][
            "faithfulness"
        ] == 1.0
    )

    average_latency_ms = (
        round(
            total_latency
            / total_cases,
            2,
        )
        if total_cases
        else 0.0
    )

    # =====================================================
    # FINAL REPORT
    # =====================================================

    return {
        "dataset": {
            "type": "generated",
            "difficulty": difficulty,
            "requested_cases": (
                sample_size
            ),
            "generated_cases": (
                total_cases
            ),
            "complete": (
                total_cases
                == sample_size
            ),
            "top_k": top_k,
        },
        "evaluation_configuration": {
            "evaluator_model": (
                settings.LLM_MODEL
            ),
            "relevance_threshold": (
                RELEVANCE_THRESHOLD
            ),
            "relevance_candidate_count": (
                RELEVANCE_CANDIDATE_COUNT
            ),
            "retrieval_metrics": [
                "Hit@K",
                "Precision@K",
                "Recall@K",
                "MRR",
                "graded_nDCG@K",
            ],
            "semantic_metrics": [
                "faithfulness",
                "citation_correctness",
                "citation_coverage",
            ],
        },
        "summary": {
            "retrieval_success_rate": round(
                (
                    successful_retrievals
                    / total_cases
                )
                if total_cases
                else 0.0,
                4,
            ),
            "production_valid_answer_rate": round(
                (
                    production_valid_answers
                    / total_cases
                )
                if total_cases
                else 0.0,
                4,
            ),
            "fully_faithful_answer_rate": round(
                (
                    fully_faithful_answers
                    / total_cases
                )
                if total_cases
                else 0.0,
                4,
            ),
            "hit_rate_at_k": (
                average_nested_metric(
                    "retrieval",
                    "hit_rate_at_k",
                )
            ),
            "precision_at_k": (
                average_nested_metric(
                    "retrieval",
                    "precision_at_k",
                )
            ),
            "recall_at_k": (
                average_nested_metric(
                    "retrieval",
                    "recall_at_k",
                )
            ),
            "mrr": (
                average_nested_metric(
                    "retrieval",
                    "reciprocal_rank",
                )
            ),
            "ndcg_at_k": (
                average_nested_metric(
                    "retrieval",
                    "ndcg_at_k",
                )
            ),
            "faithfulness": (
                average_nested_metric(
                    "semantic_evaluation",
                    "faithfulness",
                )
            ),
            "citation_correctness": (
                average_nested_metric(
                    "semantic_evaluation",
                    "citation_correctness",
                )
            ),
            "citation_coverage": (
                average_nested_metric(
                    "semantic_evaluation",
                    "citation_coverage",
                )
            ),
            "average_latency_ms": (
                average_latency_ms
            ),
        },
        "results": evaluation_results,
    }


# =========================================================
# GOLDEN / SMOKE REGRESSION SUITE
# =========================================================


@router.post("/run")
def run_evaluations(
    db: Session = Depends(get_db),
):
    """
    Run Evidentia's small deterministic golden
    regression suite.

    Generated evaluation measures broad system quality.
    This suite remains fixed intentionally so we can
    detect regressions after code changes.
    """

    evaluation_results = []
    total_latency = 0.0

    for case in EVALUATION_CASES:
        start_time = time.perf_counter()

        pipeline_result = (
            run_query_pipeline(
                db=db,
                query=case.question,
                top_k=case.top_k,
                filters=case.filters,
            )
        )

        answer = pipeline_result[
            "answer"
        ]

        validation = pipeline_result[
            "validation"
        ]

        results = pipeline_result[
            "_evaluation"
        ][
            "retrieved_results"
        ]

        evaluation = evaluate_case(
            case=case,
            answer=answer,
            results=results,
            validation=validation,
        )

        latency_ms = round(
            (
                time.perf_counter()
                - start_time
            )
            * 1000,
            2,
        )

        total_latency += latency_ms

        evaluation_results.append(
            {
                "case_id": case.id,
                "question": (
                    case.question
                ),
                "answer": answer,
                "filters": case.filters,
                "top_k": case.top_k,
                "context_precision": (
                    evaluation.context_precision
                ),
                "context_recall": (
                    evaluation.context_recall
                ),
                "answer_relevancy": (
                    evaluation.answer_relevancy
                ),
                "citation_accuracy": (
                    evaluation.citation_accuracy
                ),
                "faithfulness": (
                    evaluation.faithfulness
                ),
                "passed": (
                    evaluation.passed
                ),
                "latency_ms": (
                    latency_ms
                ),
            }
        )

    total_cases = len(
        evaluation_results
    )

    passed = sum(
        1
        for result
        in evaluation_results
        if result["passed"]
    )

    failed = (
        total_cases
        - passed
    )

    def average(
        metric: str,
    ) -> float:
        if total_cases == 0:
            return 0.0

        return round(
            sum(
                result[metric]
                for result
                in evaluation_results
            )
            / total_cases,
            4,
        )

    average_latency_ms = (
        round(
            total_latency
            / total_cases,
            2,
        )
        if total_cases
        else 0.0
    )

    return {
        "suite": (
            "golden_regression"
        ),
        "total_cases": total_cases,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(
            (
                passed
                / total_cases
            )
            if total_cases
            else 0.0,
            4,
        ),
        "averages": {
            "context_precision": (
                average(
                    "context_precision"
                )
            ),
            "context_recall": (
                average(
                    "context_recall"
                )
            ),
            "answer_relevancy": (
                average(
                    "answer_relevancy"
                )
            ),
            "citation_accuracy": (
                average(
                    "citation_accuracy"
                )
            ),
            "faithfulness": (
                average(
                    "faithfulness"
                )
            ),
        },
        "average_latency_ms": (
            average_latency_ms
        ),
        "results": (
            evaluation_results
        ),
    }