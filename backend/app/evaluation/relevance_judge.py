import json
import re

from groq import Groq

from app.core.config import settings


_client = None


# =========================================================
# CLIENT
# =========================================================


def get_client() -> Groq:
    global _client

    if _client is None:
        _client = Groq(
            api_key=settings.GROQ_API_KEY
        )

    return _client


# =========================================================
# JSON PARSING
# =========================================================


def clean_json_response(
    content: str,
) -> dict:
    """
    Remove optional Markdown fences and parse the
    model response as JSON.
    """

    content = content.strip()

    content = re.sub(
        r"^```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )

    content = re.sub(
        r"\s*```$",
        "",
        content,
    )

    return json.loads(
        content.strip()
    )


# =========================================================
# SINGLE BATCH JUDGMENT
# =========================================================


def _judge_batch(
    question: str,
    reference_answer: str,
    candidates: list[dict],
) -> dict[str, float]:
    """
    Judge one manageable batch of candidate chunks.

    Returns only judgments successfully produced by
    the evaluator. Completeness is enforced by the
    outer orchestration function.
    """

    if not candidates:
        return {}

    candidate_payload = [
        {
            "chunk_id": str(
                candidate["chunk_id"]
            ),
            "filename": candidate.get(
                "filename"
            ),
            "page_number": candidate.get(
                "page_number"
            ),
            "content": candidate.get(
                "content",
                "",
            ),
        }
        for candidate in candidates
    ]

    prompt = f"""
You are a strict relevance assessor for an enterprise
Retrieval-Augmented Generation evaluation system.

Your task is NOT to answer the question.

Your task is to determine how much evidence EACH
candidate chunk provides for answering the question.

QUESTION:
{question}

REFERENCE ANSWER:
{reference_answer}

CANDIDATE CHUNKS:
{json.dumps(candidate_payload, indent=2)}

Judge every candidate independently using ONLY its
content.

RELEVANCE SCALE:

3 = DIRECT / SUFFICIENT
The chunk directly contains enough evidence to answer
the question correctly, either by itself or almost
entirely.

2 = PARTIAL EVIDENCE
The chunk contains important evidence needed for the
answer but is not sufficient by itself.

1 = TOPICALLY RELATED
The chunk discusses the same topic but does not provide
meaningful evidence required to answer the question.

0 = IRRELEVANT
The chunk does not help answer the question.

Rules:

1. Judge evidence rather than lexical similarity.

2. A paraphrased chunk may still receive relevance 3.

3. Do not assign relevance merely because the chunk
   discusses the same broad subject.

4. Do not use outside knowledge.

5. Do not infer facts that are absent from the chunk.

6. Judge each candidate independently.

7. Return EVERY candidate exactly once.

8. Preserve each chunk_id exactly as supplied.

9. relevance must be one of: 0, 1, 2, 3.

10. Return ONLY valid JSON.

Required JSON structure:

{{
    "judgments": [
        {{
            "chunk_id": "...",
            "relevance": 0
        }}
    ]
}}
"""

    response = (
        get_client()
        .chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.0,
            max_tokens=1600,
        )
    )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    if not content:
        return {}

    parsed = clean_json_response(
        content
    )

    valid_candidate_ids = {
        str(candidate["chunk_id"])
        for candidate in candidates
    }

    judgments: dict[str, float] = {}

    for item in parsed.get(
        "judgments",
        [],
    ):
        chunk_id = str(
            item.get(
                "chunk_id",
                "",
            )
        )

        if chunk_id not in valid_candidate_ids:
            continue

        try:
            relevance = float(
                item.get(
                    "relevance",
                    0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        relevance = max(
            0.0,
            min(
                relevance,
                3.0,
            ),
        )

        judgments[
            chunk_id
        ] = relevance

    return judgments


# =========================================================
# COMPLETE RELEVANCE JUDGMENT
# =========================================================


def judge_candidate_relevance(
    question: str,
    reference_answer: str,
    candidates: list[dict],
    guaranteed_chunk_ids: list[str],
    batch_size: int = 5,
    retry_missing: bool = True,
) -> dict[str, float]:
    """
    Produce complete graded relevance judgments.

    Important guarantees:

    1. The originating source evidence remains a
       deterministic positive.

    2. Candidate judging is batched to prevent large
       prompts from causing truncated JSON responses.

    3. Missing judgments are detected explicitly.

    4. Missing candidates receive one retry.

    5. Any candidate still unjudged after retry is
       conservatively marked relevance 0 rather than
       silently disappearing.

    Scale:
        3 = direct/sufficient evidence
        2 = meaningful partial evidence
        1 = related but insufficient
        0 = irrelevant
    """

    guaranteed_ids = {
        str(chunk_id)
        for chunk_id
        in guaranteed_chunk_ids
    }

    if not candidates:
        return {
            chunk_id: 3.0
            for chunk_id
            in guaranteed_ids
        }

    # -----------------------------------------------------
    # Deduplicate candidate pool
    # -----------------------------------------------------

    unique_candidates = []
    seen_ids = set()

    for candidate in candidates:
        chunk_id = str(
            candidate["chunk_id"]
        )

        if chunk_id in seen_ids:
            continue

        seen_ids.add(
            chunk_id
        )

        unique_candidates.append(
            candidate
        )

    all_candidate_ids = {
        str(candidate["chunk_id"])
        for candidate
        in unique_candidates
    }

    judgments: dict[str, float] = {}

    # -----------------------------------------------------
    # Judge in small batches
    # -----------------------------------------------------

    for start in range(
        0,
        len(unique_candidates),
        batch_size,
    ):
        batch = unique_candidates[
            start:start + batch_size
        ]

        try:
            batch_judgments = _judge_batch(
                question=question,
                reference_answer=reference_answer,
                candidates=batch,
            )

            judgments.update(
                batch_judgments
            )

        except Exception as exc:
            print(
                "Relevance batch judging failed: "
                f"{exc}"
            )

    # -----------------------------------------------------
    # Detect missing judgments
    # -----------------------------------------------------

    missing_ids = (
        all_candidate_ids
        - set(judgments.keys())
    )

    # -----------------------------------------------------
    # Retry only missing candidates
    # -----------------------------------------------------

    if (
        missing_ids
        and retry_missing
    ):
        missing_candidates = [
            candidate
            for candidate
            in unique_candidates
            if str(
                candidate["chunk_id"]
            ) in missing_ids
        ]

        for start in range(
            0,
            len(missing_candidates),
            batch_size,
        ):
            batch = missing_candidates[
                start:start + batch_size
            ]

            try:
                retry_judgments = (
                    _judge_batch(
                        question=question,
                        reference_answer=(
                            reference_answer
                        ),
                        candidates=batch,
                    )
                )

                judgments.update(
                    retry_judgments
                )

            except Exception as exc:
                print(
                    "Relevance judgment retry "
                    f"failed: {exc}"
                )

    # -----------------------------------------------------
    # Explicit fallback
    # -----------------------------------------------------

    still_missing = (
        all_candidate_ids
        - set(judgments.keys())
    )

    for chunk_id in still_missing:
        judgments[
            chunk_id
        ] = 0.0

    # -----------------------------------------------------
    # Deterministic guaranteed positives
    # -----------------------------------------------------

    for chunk_id in guaranteed_ids:
        judgments[
            chunk_id
        ] = max(
            judgments.get(
                chunk_id,
                0.0,
            ),
            3.0,
        )

    return judgments


# =========================================================
# POSITIVE EVIDENCE
# =========================================================


def get_positive_chunk_ids(
    judgments: dict[str, float],
    minimum_relevance: float = 2.0,
) -> list[str]:
    """
    Return chunks considered meaningful retrieval
    ground truth.

    Relevance 1 is excluded because topical
    similarity alone is not evidence.
    """

    return [
        chunk_id
        for chunk_id, relevance
        in judgments.items()
        if relevance >= minimum_relevance
    ]


# =========================================================
# DIAGNOSTICS
# =========================================================


def summarize_relevance_judgments(
    judgments: dict[str, float],
) -> dict:
    """
    Produce diagnostics that can later be surfaced
    inside Evidentia's Evaluation Lab.
    """

    distribution = {
        "direct": 0,
        "partial": 0,
        "related": 0,
        "irrelevant": 0,
    }

    for relevance in judgments.values():
        if relevance >= 3:
            distribution["direct"] += 1
        elif relevance >= 2:
            distribution["partial"] += 1
        elif relevance >= 1:
            distribution["related"] += 1
        else:
            distribution[
                "irrelevant"
            ] += 1

    return {
        "total_judged": len(
            judgments
        ),
        "positive_chunks": sum(
            1
            for relevance
            in judgments.values()
            if relevance >= 2
        ),
        "distribution": distribution,
    }