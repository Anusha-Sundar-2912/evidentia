import type {
  AskRequest,
  AskResponse,
  Dataset,
  DocumentReceipt,
  EvalParams,
  EvaluationReport,
  Health,
  Ready,
  SearchResponse,
  InputGuardrail,
} from "../types/api";
export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "/api/v1"
).replace(/\/$/, "");
export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
    public code?: string,
    public retryable = false,
    public guardrails?: InputGuardrail,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(
      "Cannot reach Evidentia. Check that the backend is running, then try again.",
      0,
      "network_error",
      true,
    );
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const validation = Array.isArray(detail)
      ? detail
          .map(
            (v: { loc?: string[]; msg?: string }) =>
              `${v.loc?.join(".") || "Input"}: ${v.msg}`,
          )
          .join("; ")
      : undefined;
    const message =
      data?.message ||
      (typeof detail === "string" ? detail : detail?.message) ||
      validation ||
      {
        429: "The model provider is rate limited. Wait before trying again.",
        502: "The model provider could not complete this request.",
        503: "The model provider is temporarily unavailable.",
      }[response.status] ||
      `Request failed (${response.status}). Please try again.`;
    throw new ApiError(
      message,
      response.status,
      data?.error,
      data?.retryable ?? false,
      detail?.guardrails,
    );
  }
  if (data === null)
    throw new ApiError(
      "The server returned an unreadable response.",
      response.status,
    );
  return data as T;
}
const post = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: "POST",
    ...(body !== undefined
      ? {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : {}),
  });
export const api = {
  ask: (body: AskRequest) => post<AskResponse>("/query/ask", body),
  search: (
    mode: "semantic" | "bm25" | "hybrid",
    body: Omit<AskRequest, "conversation_id">,
  ) => post<SearchResponse>(`/query/search/${mode}`, body),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<DocumentReceipt>("/documents/upload", {
      method: "POST",
      body,
    });
  },
  health: () => request<Health>("/health"),
  ready: () => request<Ready>("/ready"),
  generate: ({ sample_size, difficulty }: EvalParams) =>
    post<Dataset>(
      `/evaluations/generate?${new URLSearchParams({ sample_size: String(sample_size), difficulty })}`,
    ),
  evaluate: (p: EvalParams) =>
    post<EvaluationReport>(
      `/evaluations/run-generated?${new URLSearchParams({ sample_size: String(p.sample_size), difficulty: p.difficulty, top_k: String(p.top_k) })}`,
    ),
};
