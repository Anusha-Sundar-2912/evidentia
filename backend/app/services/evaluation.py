import re
from dataclasses import dataclass, field


@dataclass
class EvaluationCase:
    id: str
    question: str

    expected_answer_terms: list[str] = field(
        default_factory=list
    )
    expected_evidence_terms: list[str] = field(
        default_factory=list
    )
    expected_filenames: list[str] = field(
        default_factory=list
    )
    expected_pages: list[int] = field(
        default_factory=list
    )

    # Optional retrieval configuration
    filters: dict | None = None
    top_k: int = 5

    # Expected system behaviour
    should_refuse: bool = False


@dataclass
class EvaluationResult:
    case_id: str
    context_precision: float
    context_recall: float
    answer_relevancy: float
    citation_accuracy: float
    faithfulness: float
    passed: bool


def normalize_text(text: str) -> str:
    """
    Normalize text for deterministic evaluation.

    Examples:
    eight -> 8
    32 GB -> 32gb
    32GB -> 32gb
    V100 -> v100
    """

    text = text.lower()

    number_words = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
    }

    for word, number in number_words.items():
        text = re.sub(
            rf"\b{word}\b",
            number,
            text,
        )

    # Normalize storage units:
    # "32 GB" and "32GB" both become "32gb".
    text = re.sub(
        r"(\d+)\s+(gb|mb|tb|kb)\b",
        r"\1\2",
        text,
    )

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def calculate_context_precision(
    results: list[dict],
    expected_evidence_terms: list[str],
    expected_filenames: list[str],
) -> float:
    """
    Measures how many retrieved chunks contain
    expected evidence.

    This does not assume that every chunk outside
    a known gold page is irrelevant.
    """

    if not results:
        return 0.0

    if not expected_evidence_terms:
        return 1.0

    normalized_terms = [
        normalize_text(term)
        for term in expected_evidence_terms
    ]

    relevant_chunks = 0

    for result in results:
        filename = result.get(
            "filename"
        )

        if (
            expected_filenames
            and filename
            not in expected_filenames
        ):
            continue

        content = normalize_text(
            result.get(
                "content",
                "",
            )
        )

        contains_evidence = any(
            term in content
            for term in normalized_terms
        )

        if contains_evidence:
            relevant_chunks += 1

    return round(
        relevant_chunks / len(results),
        4,
    )


def calculate_context_recall(
    results: list[dict],
    expected_filenames: list[str],
    expected_pages: list[int],
) -> float:
    """
    Measures whether known gold evidence
    locations were successfully retrieved.
    """

    if not expected_pages:
        if not expected_filenames:
            return 1.0

        retrieved_filenames = {
            result.get("filename")
            for result in results
        }

        expected = set(
            expected_filenames
        )

        if not expected:
            return 1.0

        return round(
            len(
                expected
                & retrieved_filenames
            )
            / len(expected),
            4,
        )

    retrieved_pages = {
        result.get("page_number")
        for result in results
        if (
            not expected_filenames
            or result.get("filename")
            in expected_filenames
        )
    }

    expected = set(
        expected_pages
    )

    return round(
        len(
            expected
            & retrieved_pages
        )
        / len(expected),
        4,
    )


def calculate_answer_relevancy(
    answer: str,
    expected_terms: list[str],
) -> float:
    """
    Deterministic answer relevancy proxy.

    Measures coverage of expected answer
    concepts.
    """

    if not expected_terms:
        return 1.0

    normalized_answer = normalize_text(
        answer
    )

    matched = sum(
        1
        for term in expected_terms
        if normalize_text(term)
        in normalized_answer
    )

    return round(
        matched / len(expected_terms),
        4,
    )


def calculate_citation_accuracy(
    citation_numbers: list[int],
    results: list[dict],
    expected_filenames: list[str],
    expected_pages: list[int],
) -> float:
    """
    Measures whether citations point to known
    gold evidence locations.
    """

    if not citation_numbers:
        return 0.0

    valid_citations = 0
    evaluated_citations = 0

    for number in citation_numbers:
        if not (
            1 <= number <= len(results)
        ):
            continue

        evaluated_citations += 1

        result = results[
            number - 1
        ]

        filename_match = (
            not expected_filenames
            or result.get("filename")
            in expected_filenames
        )

        page_match = (
            not expected_pages
            or result.get("page_number")
            in expected_pages
        )

        if (
            filename_match
            and page_match
        ):
            valid_citations += 1

    if evaluated_citations == 0:
        return 0.0

    return round(
        valid_citations
        / evaluated_citations,
        4,
    )


def evaluate_case(
    case: EvaluationCase,
    answer: str,
    results: list[dict],
    validation: dict,
) -> EvaluationResult:
    refusal_message = (
        "I could not find enough evidence "
        "in the available documents."
    )

    is_refusal = (
        answer.strip()
        == refusal_message
    )

    # -----------------------------------------------------
    # Refusal evaluation
    # -----------------------------------------------------

    if case.should_refuse:
        passed = is_refusal

        score = (
            1.0
            if passed
            else 0.0
        )

        return EvaluationResult(
            case_id=case.id,
            context_precision=score,
            context_recall=score,
            answer_relevancy=score,
            citation_accuracy=score,
            faithfulness=score,
            passed=passed,
        )

    # -----------------------------------------------------
    # Standard answer evaluation
    # -----------------------------------------------------

    context_precision = (
        calculate_context_precision(
            results=results,
            expected_evidence_terms=(
                case.expected_evidence_terms
            ),
            expected_filenames=(
                case.expected_filenames
            ),
        )
    )

    context_recall = (
        calculate_context_recall(
            results=results,
            expected_filenames=(
                case.expected_filenames
            ),
            expected_pages=(
                case.expected_pages
            ),
        )
    )

    answer_relevancy = (
        calculate_answer_relevancy(
            answer=answer,
            expected_terms=(
                case.expected_answer_terms
            ),
        )
    )

    citation_accuracy = (
        calculate_citation_accuracy(
            citation_numbers=validation.get(
                "citations_found",
                [],
            ),
            results=results,
            expected_filenames=(
                case.expected_filenames
            ),
            expected_pages=(
                case.expected_pages
            ),
        )
    )

    faithfulness = float(
        validation.get(
            "groundedness_score",
            0.0,
        )
    )

    # Context precision is intentionally not part
    # of pass/fail yet because it is a diagnostic
    # retrieval metric that we are still calibrating.
    passed = (
        validation.get(
            "valid",
            False,
        )
        and context_recall >= 0.5
        and answer_relevancy >= 0.5
        and citation_accuracy >= 0.5
        and faithfulness >= 0.5
    )

    return EvaluationResult(
        case_id=case.id,
        context_precision=context_precision,
        context_recall=context_recall,
        answer_relevancy=answer_relevancy,
        citation_accuracy=citation_accuracy,
        faithfulness=round(
            faithfulness,
            4,
        ),
        passed=passed,
    )