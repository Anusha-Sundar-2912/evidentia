import json
import re

from groq import Groq

from app.core.config import settings


_client = None


# =========================================================
# GROQ CLIENT
# =========================================================


def get_client() -> Groq:
    """
    Lazily initialize and reuse the Groq client.
    """

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
    Parse JSON even when the model wraps the response
    inside Markdown code fences.
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
# CLAIM EXTRACTION
# =========================================================


def extract_atomic_claims(
    answer: str,
) -> list[str]:
    """
    Break an AI-generated answer into independently
    verifiable factual claims.

    Example:

        "NIST defines four functions: GOVERN and MAP..."

    becomes atomic statements that can each be checked
    against retrieved evidence.
    """

    if not answer.strip():
        return []

    prompt = f"""
You are analyzing an answer produced by an enterprise
Retrieval-Augmented Generation system.

Decompose the answer into atomic, independently
verifiable factual claims.

ANSWER:
{answer}

Rules:

1. Each claim must express exactly one factual
   proposition whenever possible.

2. Preserve the meaning of the original answer.

3. Do not introduce information that does not appear
   in the answer.

4. Remove citation markers such as [1], [2], 【1】,
   or 【2】 from the claims.

5. Ignore headings and purely stylistic text.

6. Do not merge unrelated factual statements into
   one claim.

7. Do not judge whether the claims are correct yet.

8. Return ONLY valid JSON.

Required format:

{{
    "claims": [
        "First factual claim.",
        "Second factual claim."
    ]
}}
"""

    try:
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
                max_tokens=800,
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            return []

        parsed = clean_json_response(
            content
        )

        raw_claims = parsed.get(
            "claims",
            [],
        )

        if not isinstance(
            raw_claims,
            list,
        ):
            return []

        claims = []

        for claim in raw_claims:
            claim = str(
                claim
            ).strip()

            if claim:
                claims.append(
                    claim
                )

        return claims

    except Exception as exc:
        print(
            "Claim extraction failed: "
            f"{exc}"
        )

        return []


# =========================================================
# EVIDENCE CONSTRUCTION
# =========================================================


def build_evidence_payload(
    results: list[dict],
) -> list[dict]:
    """
    Convert production retrieval results into a compact
    evidence representation for semantic verification.

    source_number matches Evidentia's citation numbering.
    """

    evidence = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        evidence.append(
            {
                "source_number": index,
                "chunk_id": str(
                    result["chunk_id"]
                ),
                "filename": result.get(
                    "filename"
                ),
                "page_number": result.get(
                    "page_number"
                ),
                "content": result.get(
                    "content",
                    "",
                ),
            }
        )

    return evidence


# =========================================================
# CLAIM ↔ EVIDENCE VERIFICATION
# =========================================================


def judge_claims(
    claims: list[str],
    evidence: list[dict],
) -> list[dict]:
    """
    Semantically determine whether each atomic claim is
    supported by the retrieved evidence.

    This replaces lexical overlap as the serious
    evaluation-time faithfulness measurement.
    """

    if not claims:
        return []

    if not evidence:
        return [
            {
                "claim": claim,
                "supported": False,
                "supporting_sources": [],
            }
            for claim in claims
        ]

    prompt = f"""
You are a strict evidence verifier for an enterprise
Retrieval-Augmented Generation system.

You must determine whether each factual claim is
supported by the retrieved evidence.

CLAIMS:
{json.dumps(claims, indent=2)}

RETRIEVED EVIDENCE:
{json.dumps(evidence, indent=2)}

For EVERY claim:

- Determine whether the retrieved evidence supports it.
- Identify which source_number values provide that
  support.

A claim is SUPPORTED when the evidence directly states
the claim or clearly entails the same factual meaning.

A claim is UNSUPPORTED when:

- the evidence contradicts it,
- the evidence does not contain enough information,
- it requires outside knowledge,
- or the evidence merely discusses the same broad topic.

Important rules:

1. Evaluate semantic meaning, not word overlap.

2. Paraphrasing is allowed.

3. Do not use outside knowledge.

4. Do not infer unsupported details.

5. A claim may be supported by multiple sources.

6. Only include source numbers that actually support
   the claim.

7. Return EVERY supplied claim exactly once.

8. Preserve the claim text exactly.

9. Return ONLY valid JSON.

Required format:

{{
    "judgments": [
        {{
            "claim": "...",
            "supported": true,
            "supporting_sources": [1, 2]
        }}
    ]
}}
"""

    try:
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
            raise ValueError(
                "Empty claim judgment response."
            )

        parsed = clean_json_response(
            content
        )

        raw_judgments = parsed.get(
            "judgments",
            [],
        )

        # Match returned judgments by exact claim text
        # instead of trusting the LLM's array order.
        returned_by_claim = {}

        for item in raw_judgments:
            claim_text = str(
                item.get(
                    "claim",
                    "",
                )
            ).strip()

            if claim_text:
                returned_by_claim[
                    claim_text
                ] = item

        normalized = []

        for claim in claims:
            item = returned_by_claim.get(
                claim,
                {},
            )

            raw_sources = item.get(
                "supporting_sources",
                [],
            )

            valid_sources = []

            if isinstance(
                raw_sources,
                list,
            ):
                for source in raw_sources:
                    try:
                        source_number = int(
                            source
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                    if (
                        1
                        <= source_number
                        <= len(evidence)
                    ):
                        valid_sources.append(
                            source_number
                        )

            supported = bool(
                item.get(
                    "supported",
                    False,
                )
            )

            # A supported claim must identify at least
            # one concrete supporting evidence source.
            if (
                supported
                and not valid_sources
            ):
                supported = False

            normalized.append(
                {
                    "claim": claim,
                    "supported": supported,
                    "supporting_sources": sorted(
                        set(
                            valid_sources
                        )
                    ),
                }
            )

        return normalized

    except Exception as exc:
        print(
            "Claim verification failed: "
            f"{exc}"
        )

        # Conservative failure mode:
        # evaluator failure must never magically
        # increase the faithfulness score.
        return [
            {
                "claim": claim,
                "supported": False,
                "supporting_sources": [],
            }
            for claim in claims
        ]


# =========================================================
# CITATION EXTRACTION
# =========================================================


def extract_answer_citations(
    answer: str,
) -> set[int]:
    """
    Extract both conventional [1] citations and
    Unicode-style 【1】 citations.
    """

    matches = re.findall(
        r"\[(\d+)\]|【(\d+)】",
        answer,
    )

    citations = set()

    for normal, unicode_style in matches:
        value = (
            normal
            or unicode_style
        )

        if value:
            citations.add(
                int(value)
            )

    return citations


# =========================================================
# CLAIM-LEVEL GROUNDING EVALUATION
# =========================================================


def evaluate_claim_grounding(
    answer: str,
    results: list[dict],
) -> dict:
    """
    Perform semantic claim-level evaluation.

    Metrics
    -------

    faithfulness:
        Percentage of generated factual claims that
        are supported by retrieved evidence.

    citation_correctness:
        Percentage of citation source numbers used by
        the answer that actually support at least one
        generated claim.

    citation_coverage:
        Percentage of supported claims for which the
        answer cites at least one supporting source.

    Note:
        citation_coverage currently measures citation
        presence across the answer. It does not yet
        guarantee sentence-level citation placement.
    """

    claims = extract_atomic_claims(
        answer
    )

    evidence = build_evidence_payload(
        results
    )

    judgments = judge_claims(
        claims=claims,
        evidence=evidence,
    )

    total_claims = len(
        judgments
    )

    supported = [
        judgment
        for judgment
        in judgments
        if judgment[
            "supported"
        ]
    ]

    unsupported = [
        judgment
        for judgment
        in judgments
        if not judgment[
            "supported"
        ]
    ]

    # -----------------------------------------------------
    # Faithfulness
    # -----------------------------------------------------

    faithfulness = (
        len(supported)
        / total_claims
        if total_claims
        else 0.0
    )

    # -----------------------------------------------------
    # Citations actually present in generated answer
    # -----------------------------------------------------

    answer_citations = (
        extract_answer_citations(
            answer
        )
    )

    # -----------------------------------------------------
    # Sources that genuinely support generated claims
    # -----------------------------------------------------

    supporting_sources = {
        source
        for judgment
        in supported
        for source
        in judgment[
            "supporting_sources"
        ]
    }

    # -----------------------------------------------------
    # Citation correctness
    # -----------------------------------------------------

    if answer_citations:
        citation_correctness = (
            len(
                answer_citations
                & supporting_sources
            )
            / len(
                answer_citations
            )
        )

    elif supported:
        citation_correctness = 0.0

    else:
        citation_correctness = 1.0

    # -----------------------------------------------------
    # Citation coverage
    # -----------------------------------------------------

    if supported:
        supported_with_citation = sum(
            1
            for judgment
            in supported
            if (
                set(
                    judgment[
                        "supporting_sources"
                    ]
                )
                & answer_citations
            )
        )

        citation_coverage = (
            supported_with_citation
            / len(supported)
        )

    else:
        citation_coverage = 0.0

    return {
        "faithfulness": round(
            faithfulness,
            4,
        ),
        "citation_correctness": round(
            citation_correctness,
            4,
        ),
        "citation_coverage": round(
            citation_coverage,
            4,
        ),
        "total_claims": total_claims,
        "supported_claims": len(
            supported
        ),
        "unsupported_claims": len(
            unsupported
        ),
        "answer_citations": sorted(
            answer_citations
        ),
        "supporting_sources": sorted(
            supporting_sources
        ),
        "claim_judgments": judgments,
    }