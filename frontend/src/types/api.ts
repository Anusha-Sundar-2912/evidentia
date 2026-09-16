export interface DocumentReceipt {
  id: string;
  filename: string;
  source_type: string;
  status: string;
  chunk_count: number;
  created_at: string;
}
export interface Filters {
  filenames?: string[];
  source_types?: string[];
  page_numbers?: number[];
}
export interface AskRequest {
  query: string;
  top_k: number;
  filters?: Filters;
  conversation_id?: string;
}
export interface Citation {
  source_number: number;
  filename: string;
  page_number: number | null;
  chunk_id: string;
}
export interface Validation {
  valid: boolean;
  citations_present: boolean;
  citations_found: number[];
  invalid_citations: number[];
  grounded: boolean;
  groundedness_score: number;
}
export interface InputGuardrail {
  allowed: boolean;
  prompt_injection_detected: boolean;
  pii_detected: boolean;
  pii_types: string[];
  pii_redacted?: boolean;
  reasons: string[];
}
export interface Guardrails {
  input: InputGuardrail;
  output: { safe: boolean; pii_detected: boolean; pii_types: string[] };
}
export interface SelectedChunk {
  rank: number;
  chunk_id: string;
  filename: string;
  page_number: number | null;
  reranker_score: number | null;
}
export interface Trace {
  original_query: string;
  sanitized_query: string;
  rewritten_query: string;
  subqueries: string[];
  retrieved_chunk_count: number;
  selected_chunks: SelectedChunk[];
  compression: {
    original_context_chars: number;
    compressed_context_chars: number;
    chars_saved: number;
    compression_ratio: number;
  };
  latency_ms: Record<string, number>;
}
export interface AskResponse {
  query: string;
  answer: string;
  citations: Citation[];
  validation: Validation;
  guardrails: Guardrails;
  trace: Trace;
  conversation_id: string;
}
export interface SearchResult {
  chunk_id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  filename: string;
  score: number;
  reranker_score: number | null;
}
export interface SearchResponse {
  query: string;
  mode: string;
  results: SearchResult[];
}
export interface Health {
  status: string;
  service: string;
  version: string;
}
export interface Ready extends Health {
  checks: { postgres: boolean; redis: boolean };
}
export type Difficulty = "direct" | "paraphrase" | "deep_retrieval";
export interface EvalParams {
  sample_size: number;
  difficulty: Difficulty;
  top_k: number;
}
export interface GeneratedCase {
  id: string;
  question: string;
  reference_answer: string;
  source_document: string;
  source_document_id: string;
  source_chunk_ids: string[];
  source_pages: number[];
  evidence: string[];
  difficulty: string;
  evaluation_type: string;
  answerable: boolean;
}
export interface Dataset {
  requested_cases: number;
  generated_cases: number;
  difficulty: string;
  complete: boolean;
  cases: GeneratedCase[];
}
export interface ClaimJudgment {
  claim: string;
  supported: boolean;
  supporting_sources: number[];
}
export interface EvaluationCase {
  case_id: string;
  difficulty: string;
  evaluation_type: string;
  question: string;
  reference_answer: string;
  answer: string;
  ground_truth: {
    originating_document: string;
    originating_pages: number[];
    originating_chunk_ids: string[];
    relevant_chunk_ids: string[];
    relevance_judgments: Record<string, number>;
    relevance_diagnostics: {
      total_judged: number;
      positive_chunks: number;
      distribution: Record<string, number>;
    };
  };
  retrieval: Record<string, number>;
  semantic_evaluation: {
    faithfulness: number;
    citation_correctness: number;
    citation_coverage: number;
    total_claims: number;
    supported_claims: number;
    unsupported_claims: number;
    answer_citations: number[];
    supporting_sources: number[];
    claim_judgments: ClaimJudgment[];
  };
  production_validation: Validation;
  citations: Citation[];
  latency_ms: number;
}
export interface EvaluationReport {
  dataset: {
    type: string;
    difficulty: string;
    requested_cases: number;
    generated_cases: number;
    complete: boolean;
    top_k: number;
  };
  evaluation_configuration: {
    evaluator_model: string;
    relevance_threshold: number;
    relevance_candidate_count: number;
    retrieval_metrics: string[];
    semantic_metrics: string[];
  };
  summary: Record<string, number>;
  results: EvaluationCase[];
}
