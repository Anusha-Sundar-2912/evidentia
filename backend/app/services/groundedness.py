import re


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_cited_results(
    citation_numbers: list[int],
    results: list[dict],
) -> list[dict]:
    cited_results = []

    for number in citation_numbers:
        index = number - 1

        if 0 <= index < len(results):
            cited_results.append(results[index])

    return cited_results


def calculate_groundedness(
    answer: str,
    citation_numbers: list[int],
    results: list[dict],
) -> dict:
    if not citation_numbers:
        return {
            "grounded": False,
            "groundedness_score": 0.0,
        }

    cited_results = get_cited_results(
        citation_numbers=citation_numbers,
        results=results,
    )

    if not cited_results:
        return {
            "grounded": False,
            "groundedness_score": 0.0,
        }

    evidence = " ".join(
        result["content"]
        for result in cited_results
    )

    normalized_answer = normalize_text(answer)
    normalized_evidence = normalize_text(evidence)

    answer_words = {
        word
        for word in normalized_answer.split()
        if len(word) > 3
        and not word.isdigit()
    }

    evidence_words = set(
        normalized_evidence.split()
    )

    if not answer_words:
        return {
            "grounded": False,
            "groundedness_score": 0.0,
        }

    supported_words = (
        answer_words & evidence_words
    )

    score = (
        len(supported_words)
        / len(answer_words)
    )

    score = round(score, 4)

    return {
        "grounded": score >= 0.6,
        "groundedness_score": score,
    }