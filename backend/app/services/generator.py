import json

import groq
from groq import Groq

from app.core.config import settings
from app.core.exceptions import (
    LLMProviderError,
    LLMRateLimitError,
    LLMUnavailableError,
)


_client = None


def get_client() -> Groq:
    global _client

    if _client is None:
        _client = Groq(
            api_key=settings.GROQ_API_KEY
        )

    return _client


def handle_llm_exception(
    exc: Exception,
) -> None:
    """
    Translate provider-specific failures into
    Evidentia domain exceptions.

    This prevents raw provider errors from leaking
    through the API as generic HTTP 500 responses.
    """

    if isinstance(
        exc,
        groq.RateLimitError,
    ):
        raise LLMRateLimitError() from exc

    if isinstance(
        exc,
        (
            groq.APIConnectionError,
            groq.APITimeoutError,
        ),
    ):
        raise LLMUnavailableError() from exc

    if isinstance(
        exc,
        groq.APIStatusError,
    ):
        if exc.status_code >= 500:
            raise LLMUnavailableError() from exc

        raise LLMProviderError(
            message=(
                "The language model provider "
                "rejected the request."
            ),
            retryable=False,
        ) from exc

    raise LLMProviderError(
        message=(
            "The language model request failed."
        ),
        retryable=False,
    ) from exc


def decompose_query(
    query: str,
    max_queries: int = 4,
) -> list[str]:
    """
    Break a complex question into focused retrieval
    queries.

    This is an optional enhancement. Provider failure
    must never prevent normal retrieval.
    """

    client = get_client()

    prompt = f"""
You are the query planner for an enterprise RAG system.

Break the user's question into focused retrieval queries.

Rules:

1. Preserve the meaning of the original question.
2. Split only when the question contains multiple distinct information needs.
3. Each query must be understandable independently.
4. Do not answer the question.
5. Do not add facts not present in the user's question.
6. Return at most {max_queries} queries.
7. Return ONLY valid JSON:

{{"queries": ["query 1", "query 2"]}}

User question:

{query}
""".strip()

    try:
        response = (
            client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a retrieval query "
                            "planner. Return only valid "
                            "JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.0,
                max_tokens=300,
                response_format={
                    "type": "json_object"
                },
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            return [query]

        data = json.loads(
            content
        )

        queries = data.get(
            "queries",
            [],
        )

        cleaned_queries = []

        for item in queries:
            if not isinstance(
                item,
                str,
            ):
                continue

            cleaned = item.strip()

            if (
                cleaned
                and cleaned
                not in cleaned_queries
            ):
                cleaned_queries.append(
                    cleaned
                )

        if not cleaned_queries:
            return [query]

        return cleaned_queries[
            :max_queries
        ]

    except Exception:
        # Query planning is optional and therefore
        # deliberately fails open.
        return [query]


def rewrite_query_with_history(
    query: str,
    history: list[dict],
) -> str:
    """
    Resolve conversational references using history.

    History is never considered answer evidence.
    """

    if not history:
        return query

    client = get_client()

    history_text = "\n".join(
        f"{message.get('role', 'unknown')}: "
        f"{message.get('content', '')}"
        for message in history
    )

    prompt = f"""
You are the conversational query rewriter for an
enterprise RAG system.

Rewrite the latest user question into a standalone
retrieval query.

Rules:

1. Use history only to resolve conversational references.
2. Preserve the user's original intent.
3. Do not answer the question.
4. Do not introduce unrelated facts.
5. Use the minimum necessary conversation context.
6. If already standalone, return it unchanged.
7. The result must be suitable for document retrieval.
8. Return ONLY valid JSON:

{{"query": "standalone retrieval query"}}

Conversation history:

{history_text}

Latest user question:

{query}
""".strip()

    try:
        response = (
            client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Rewrite conversational "
                            "questions into standalone "
                            "retrieval queries. Return "
                            "only valid JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.0,
                max_tokens=200,
                response_format={
                    "type": "json_object"
                },
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:
            return query

        data = json.loads(
            content
        )

        rewritten_query = data.get(
            "query",
            "",
        )

        if not isinstance(
            rewritten_query,
            str,
        ):
            return query

        rewritten_query = (
            rewritten_query.strip()
        )

        return (
            rewritten_query
            if rewritten_query
            else query
        )

    except Exception:
        # Conversational rewriting is optional.
        return query


def build_context(
    results: list[dict],
) -> str:
    context_parts = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        page = result.get(
            "page_number"
        )

        source = (
            f"[{index}] "
            f"{result['filename']} "
            f"(page {page})"
        )

        context_parts.append(
            f"{source}\n"
            f"{result['content']}"
        )

    return "\n\n".join(
        context_parts
    )


def build_prompt(
    query: str,
    results: list[dict],
) -> str:
    context = build_context(
        results
    )

    return f"""
You are Evidentia, an enterprise knowledge intelligence assistant.

Answer the user's question using ONLY the provided context.

STRICT RULES:

1. Do not use outside knowledge.
2. Do not invent or infer unsupported information.
3. Every factual claim must be supported by the provided sources.
4. Cite sources ONLY using the exact format [1], [2], [3], etc.
5. NEVER create line numbers, page ranges, URLs, or citation formats
   such as 【1†L1-L3】.
6. A citation number must correspond to one of the supplied sources.
7. If multiple sources support a claim, citations may be combined:
   [1] [2]
8. If the documents do not contain enough evidence, respond exactly:
   "I could not find enough evidence in the available documents."
9. When the question contains multiple parts, answer each part only
   when supporting evidence exists.
10. Be concise and direct.
11. Do not repeat the same point in multiple forms.
12. Every factual sentence must be supported by cited context.
13. Never end with an unfinished sentence.

User question:

{query}

Context:

{context}

Answer:
""".strip()


def generate_answer(
    query: str,
    results: list[dict],
) -> str:
    """
    Generate the final evidence-grounded answer.

    Unlike optional query-planning stages, final answer
    generation is essential. Provider failures therefore
    propagate as structured Evidentia exceptions.
    """

    client = get_client()

    prompt = build_prompt(
        query=query,
        results=results,
    )

    try:
        response = (
            client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a grounded "
                            "enterprise document "
                            "question-answering system."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.1,
                max_tokens=900,
            )
        )

    except Exception as exc:
        handle_llm_exception(
            exc
        )

    answer = (
        response
        .choices[0]
        .message
        .content
    )

    if not answer:
        return (
            "I could not generate an answer "
            "from the available documents."
        )

    return answer.strip()