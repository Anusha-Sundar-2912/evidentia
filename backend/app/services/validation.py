import re

from app.services.groundedness import calculate_groundedness


REFUSAL_MESSAGE = (
    "I could not find enough evidence "
    "in the available documents."
)


def is_refusal(answer: str) -> bool:
    return answer.strip() == REFUSAL_MESSAGE


def extract_citations(answer: str) -> list[int]:
    patterns = [
        r"\[(\d+)\]",
        r"【(\d+)】",
    ]

    citations = []

    for pattern in patterns:
        matches = re.findall(
            pattern,
            answer,
        )

        citations.extend(
            int(match)
            for match in matches
        )

    return sorted(set(citations))


def validate_citations(
    answer: str,
    results: list[dict],
) -> dict:
    citation_numbers = extract_citations(
        answer
    )

    valid_numbers = set(
        range(1, len(results) + 1)
    )

    invalid_citations = [
        number
        for number in citation_numbers
        if number not in valid_numbers
    ]

    return {
        "valid": len(invalid_citations) == 0,
        "citations_found": citation_numbers,
        "invalid_citations": invalid_citations,
    }


def validate_answer(
    answer: str,
    results: list[dict],
) -> dict:
    refusal = is_refusal(answer)

    citation_validation = validate_citations(
        answer=answer,
        results=results,
    )

    citations_found = citation_validation[
        "citations_found"
    ]

    citations_present = (
        len(citations_found) > 0
    )

    # A correct refusal is valid even though
    # it intentionally contains no citations.
    if refusal:
        return {
            "valid": True,
            "citations_present": False,
            "citations_found": [],
            "invalid_citations": [],
            "grounded": True,
            "groundedness_score": 1.0,
        }

    groundedness = calculate_groundedness(
        answer=answer,
        citation_numbers=citations_found,
        results=results,
    )

    valid = (
        citation_validation["valid"]
        and citations_present
        and groundedness["grounded"]
    )

    return {
        "valid": valid,
        "citations_present": citations_present,
        "citations_found": citations_found,
        "invalid_citations": citation_validation[
            "invalid_citations"
        ],
        "grounded": groundedness[
            "grounded"
        ],
        "groundedness_score": groundedness[
            "groundedness_score"
        ],
    }