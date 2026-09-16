import json
import random
import re
from dataclasses import asdict, dataclass

from groq import Groq
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.rag import hybrid_candidates


_client = None

FORBIDDEN_QUESTION_PHRASES = (
    "according to the passage",
    "according to the text",
    "according to the evidence",
    "according to the provided",
    "in the passage",
    "in the provided text",
    "based on the passage",
    "based on the provided text",
)


@dataclass
class GeneratedEvaluationCase:
    id: str
    question: str
    reference_answer: str
    source_document: str
    source_document_id: str
    source_chunk_ids: list[str]
    source_pages: list[int]
    evidence: list[str]
    difficulty: str
    evaluation_type: str
    answerable: bool = True


def get_client() -> Groq:
    global _client

    if _client is None:
        _client = Groq(
            api_key=settings.GROQ_API_KEY
        )

    return _client


def clean_json_response(
    content: str,
) -> dict:
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


def select_candidate_chunks(
    db: Session,
    sample_size: int = 10,
    min_chars: int = 300,
) -> list[Chunk]:
    chunks = (
        db.query(Chunk)
        .join(Document)
        .filter(
            Chunk.content.isnot(None)
        )
        .all()
    )

    candidates = [
        chunk
        for chunk in chunks
        if len(
            chunk.content.strip()
        ) >= min_chars
    ]

    if len(candidates) <= sample_size:
        return candidates

    return random.sample(
        candidates,
        sample_size,
    )


def question_is_valid(
    question: str,
) -> bool:
    normalized = question.lower().strip()

    if len(normalized) < 10:
        return False

    return not any(
        phrase in normalized
        for phrase
        in FORBIDDEN_QUESTION_PHRASES
    )


def generate_case_from_chunk(
    chunk: Chunk,
    difficulty: str = "paraphrase",
) -> GeneratedEvaluationCase | None:
    document = chunk.document

    prompt = f"""
You are creating a realistic evaluation question for an
enterprise Retrieval-Augmented Generation system.

SOURCE DOCUMENT:
{document.filename}

SOURCE PAGE:
{chunk.page_number}

SOURCE EVIDENCE:
{chunk.content}

Create ONE question whose answer is fully supported by
the source evidence.

Difficulty:
{difficulty}

Requirements:

1. The question must be answerable from the evidence.
2. Do not mention the source document.
3. Do not mention the page number.
4. Do not copy a complete source sentence.
5. The reference answer must contain only supported facts.
6. Write the question as a real user would ask it.
7. Never say "according to the passage", "according to
   the text", "the provided evidence", "the passage",
   "the provided text", or similar evaluation language.
8. Do not introduce outside knowledge.
9. For paraphrase difficulty, use meaningfully different
   wording from the source.
10. For deep_retrieval difficulty, prefer a specific
    detail rather than a broad topic-level question.

Return ONLY valid JSON:

{{
    "question": "...",
    "reference_answer": "..."
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
                temperature=0.2,
                max_tokens=500,
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            return None

        parsed = clean_json_response(
            content
        )

        question = str(
            parsed.get(
                "question",
                "",
            )
        ).strip()

        reference_answer = str(
            parsed.get(
                "reference_answer",
                "",
            )
        ).strip()

        if (
            not question
            or not reference_answer
            or not question_is_valid(
                question
            )
        ):
            return None

        return GeneratedEvaluationCase(
            id=(
                f"generated_"
                f"{str(chunk.id)[:8]}"
            ),
            question=question,
            reference_answer=reference_answer,
            source_document=document.filename,
            source_document_id=str(
                document.id
            ),
            source_chunk_ids=[
                str(chunk.id)
            ],
            source_pages=(
                [chunk.page_number]
                if chunk.page_number is not None
                else []
            ),
            evidence=[
                chunk.content
            ],
            difficulty=difficulty,
            evaluation_type="single_chunk",
            answerable=True,
        )

    except Exception as exc:
        print(
            "Evaluation generation failed: "
            f"{exc}"
        )

        return None


def generate_evaluation_dataset(
    db: Session,
    sample_size: int = 10,
    difficulty: str = "paraphrase",
    max_attempt_multiplier: int = 4,
) -> list[dict]:
    """
    Attempt to return the requested number of valid
    generated cases rather than silently shrinking the
    benchmark after a failed LLM generation.
    """

    candidate_pool_size = max(
        sample_size * max_attempt_multiplier,
        sample_size,
    )

    chunks = select_candidate_chunks(
        db=db,
        sample_size=candidate_pool_size,
    )

    random.shuffle(
        chunks
    )

    generated_cases = []
    used_chunk_ids = set()

    for chunk in chunks:
        if len(generated_cases) >= sample_size:
            break

        chunk_id = str(
            chunk.id
        )

        if chunk_id in used_chunk_ids:
            continue

        used_chunk_ids.add(
            chunk_id
        )

        case = generate_case_from_chunk(
            chunk=chunk,
            difficulty=difficulty,
        )

        if case is not None:
            generated_cases.append(
                asdict(case)
            )

    return generated_cases


def discover_relevance_candidates(
    db: Session,
    question: str,
    source_chunk_ids: list[str],
    candidate_count: int = 20,
) -> list[dict]:
    """
    Build a broad candidate pool for relevance
    assessment and force known source evidence into it.
    """

    candidates = hybrid_candidates(
        db=db,
        query=question,
        top_k=candidate_count,
    )

    existing_ids = {
        str(candidate["chunk_id"])
        for candidate in candidates
    }

    missing_ids = [
        chunk_id
        for chunk_id
        in source_chunk_ids
        if str(chunk_id)
        not in existing_ids
    ]

    if missing_ids:
        source_chunks = (
            db.query(Chunk)
            .join(Document)
            .filter(
                Chunk.id.in_(
                    missing_ids
                )
            )
            .all()
        )

        for chunk in source_chunks:
            candidates.append(
                {
                    "chunk_id": str(
                        chunk.id
                    ),
                    "chunk_index": (
                        chunk.chunk_index
                    ),
                    "content": (
                        chunk.content
                    ),
                    "page_number": (
                        chunk.page_number
                    ),
                    "filename": (
                        chunk.document.filename
                    ),
                    "score": 0.0,
                }
            )

    deduplicated = []
    seen = set()

    for candidate in candidates:
        chunk_id = str(
            candidate["chunk_id"]
        )

        if chunk_id in seen:
            continue

        seen.add(
            chunk_id
        )

        deduplicated.append(
            candidate
        )

    return deduplicated