from pydantic import BaseModel, Field


class MetadataFilter(BaseModel):
    filenames: list[str] | None = None
    source_types: list[str] | None = None
    page_numbers: list[int] | None = None


class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
    )
    filters: MetadataFilter | None = None


class SearchResult(BaseModel):
    chunk_id: str
    chunk_index: int
    content: str
    page_number: int | None
    filename: str
    score: float
    reranker_score: float | None = None


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: list[SearchResult]


class AskRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )
    filters: MetadataFilter | None = None
    conversation_id: str | None = None


class Citation(BaseModel):
    source_number: int
    filename: str
    page_number: int | None
    chunk_id: str


class ValidationResult(BaseModel):
    valid: bool
    citations_present: bool
    citations_found: list[int]
    invalid_citations: list[int]
    grounded: bool
    groundedness_score: float


class InputGuardrailResult(BaseModel):
    allowed: bool
    prompt_injection_detected: bool
    pii_detected: bool
    pii_types: list[str]
    pii_redacted: bool
    reasons: list[str]


class OutputGuardrailResult(BaseModel):
    safe: bool
    pii_detected: bool
    pii_types: list[str]


class GuardrailReport(BaseModel):
    input: InputGuardrailResult
    output: OutputGuardrailResult


class SelectedChunkTrace(BaseModel):
    rank: int
    chunk_id: str
    filename: str
    page_number: int | None
    reranker_score: float | None = None


class CompressionTrace(BaseModel):
    original_context_chars: int
    compressed_context_chars: int
    chars_saved: int
    compression_ratio: float


class RetrievalTrace(BaseModel):
    original_query: str
    sanitized_query: str
    rewritten_query: str
    subqueries: list[str]
    retrieved_chunk_count: int
    selected_chunks: list[SelectedChunkTrace]
    compression: CompressionTrace
    latency_ms: dict[str, float]


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]
    validation: ValidationResult
    guardrails: GuardrailReport
    trace: RetrievalTrace
    conversation_id: str