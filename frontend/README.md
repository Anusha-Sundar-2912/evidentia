# Evidentia frontend

Evidentia's React + TypeScript frontend provides the operational interface for evidence-grounded querying, knowledge ingestion, retrieval inspection, guardrails, evaluations, and system readiness.

API credentials and other secrets belong only in server-side environment variables. Never expose provider credentials through Vite environment variables.

## Local development (Windows / PowerShell)

Terminal 1, from your existing project root:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Use your existing working PostgreSQL/Redis setup. If you use this repository's Compose services, start them from the project root with `docker compose up -d`. Do not replace a working database configuration or remove its volumes. The supplied Compose maps PostgreSQL to localhost port 5433 and Redis to 6379; the existing backend `.env` must match the setup you actually use.

Terminal 2, from the project root:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Node.js 22.12+ is recommended (Vite 7 also supports Node 20.19+). Development binds to the loopback interface. The Vite `/api` proxy forwards to `http://127.0.0.1:8000`, avoiding any backend changes. The full API prefix is `/api/v1`, not `/health` at the root.

Optional frontend configuration:

```powershell
Copy-Item .env.example .env
```

`VITE_API_BASE_URL` defaults to `/api/v1`. If using a separate API origin, include `/api/v1` in its URL and configure that origin in the backend's CORS allowlist. Vite variables are public build-time settings: never add Groq keys or database credentials.

## Production

```powershell
npm run build
npm run preview
```

`dist/` is the production output. Preview serves the compiled UI only; it does not provide the development API proxy. For a working production deployment, serve `dist/`, rewrite frontend routes to `index.html`, and reverse-proxy `/api/v1/*` to FastAPI. Alternatively build with an explicit `VITE_API_BASE_URL` and configure backend CORS. This task does not deploy a public service or add authentication to the backend.

## Routes

| Route          | Experience                                                                                                 |
| -------------- | ---------------------------------------------------------------------------------------------------------- |
| `/`            | Editorial landing, original Evi robot, conceptual evidence illustration                                    |
| `/ask`         | Questions, conversation context, filename filter, K, citations, validator and privacy results              |
| `/knowledge`   | PDF/DOCX drag-and-drop upload; browser-local confirmed upload receipts                                     |
| `/retrieval`   | Interactive returned trace, reranker values, compression, stage timings; independent passage search        |
| `/guardrails`  | Actual last query/block report; clearly labeled local email redaction demonstration                        |
| `/evaluations` | Explicit generated evaluations and dataset generation, eight metrics, cases, claim and relevance judgments |
| `/system`      | Liveness and PostgreSQL/Redis readiness, manual refresh, degraded/error states                             |

## Architecture

- `src/api/client.ts`: centralized base URL, typed fetch calls, multipart upload, structured errors. POSTs are never retried automatically.
- `src/types/api.ts`: contracts transcribed from the backend schemas and evaluation dictionaries.
- `src/pages/`: separate lazy-loaded route components.
- `src/components/evidence/`: citation-to-source selection; unsafe output suppression.
- `src/components/retrieval/`: six interactive trace views and timings. Changing display order animates actual returned chunk cards.
- `src/components/evi/`: SVG character with deterministic expression states; in-flow safe anchors that cannot cover controls; minimized guidance.
- `src/components/ui/`: errors, pending states, badges, headings and inspectable response details.
- `src/store/workspace.ts`: small external store using `useSyncExternalStore` for current query, conversation ID, Evi state, operations and task errors. No giant app context.
- `src/hooks/useReceipts.ts`: local upload receipt cache. TanStack Query also owns system data and session evaluation results.
- `src/styles/index.css`: responsive pearl/stone/sage/periwinkle design, subtle evidence lines, mobile navigation and reduced motion.
- `tests/workspace.spec.ts`: isolated browser contract fixtures; not imported into application code.

## Integrated backend contracts

All paths below are relative to `/api/v1`.

| Method | Endpoint                     | Request                                                                              |
| ------ | ---------------------------- | ------------------------------------------------------------------------------------ |
| POST   | `/documents/upload`          | Multipart field `file`; PDF or DOCX                                                  |
| POST   | `/query/ask`                 | JSON `query`, `top_k` 1-10, optional `filters.filenames`, optional `conversation_id` |
| POST   | `/query/search/semantic`     | JSON `query`, `top_k`                                                                |
| POST   | `/query/search/bm25`         | JSON `query`, `top_k`                                                                |
| POST   | `/query/search/hybrid`       | JSON `query`, `top_k`                                                                |
| POST   | `/evaluations/generate`      | URL query parameters `sample_size` 1-25 and `difficulty`                             |
| POST   | `/evaluations/run-generated` | URL query parameters `sample_size` 1-25, `difficulty`, `top_k` 1-20                  |
| GET    | `/health`                    | No parameters                                                                        |
| GET    | `/ready`                     | No parameters                                                                        |

Evaluation difficulty values are `direct`, `paraphrase`, `deep_retrieval`. The fixed `/evaluations/run` regression suite is not exposed in the UI because it is tied to the backend's bundled golden cases rather than the current knowledge base.

## Honest capability boundaries

1. **No document list/detail/delete API.** Knowledge shows confirmed upload receipts from this browser, with status explicitly labeled "at upload." These are not live inventory. Local storage is keyed by API base URL; they can become stale if a backend is replaced at the same URL. Ask is not blocked when receipts are empty, because existing backend documents may be present. No fake fetch/list endpoint exists.
2. **No streaming, task IDs or progress endpoints.** Upload, query and evaluations use a general processing state with elapsed waiting time. No simulated parsing/retrieval/verification progress. Returning to a pending route restarts its visible timer; it does not restart the backend task. Refreshing the browser loses in-flight UI state; a backend task might still finish. Avoid resubmitting expensive work until you check the backend.
3. **Ask does not expose passage text or original candidates.** Citations show exact returned filenames/pages/chunk IDs. Independent search can fetch real passages, but is explicitly labeled a separate request. It is never presented as the prior answer's candidate set.
4. **Trace semantics.** `retrieved_chunk_count` counts final selected chunks in this implementation, not all pre-rerank candidates. The UI labels it accordingly. `original_query` is already sanitized by the backend. Candidate reorder animations change the display of actual returned rows; they do not pretend to replay unavailable intermediate ranking.
5. **Groundedness is word overlap.** The production validator is a lexical heuristic, not semantic entailment or confidence. A correct refusal is valid with score 1.0 and no citations. The UI treats this as insufficient evidence, not a perfect-confidence answer.
6. **Evaluation limitations.** Metrics are backend-returned, model-assisted judgments. The backend can return partial/zero-case runs; zero-case aggregates are hidden. Precision divides by the number of returned chunks, not always K. Recall is relative to the candidate pool judged relevant, not exhaustive document relevance. Retrieved passages are not included in the generated run response. Origin IDs, relevance grades, citations and claim judgments are exposed. "Generate questions only" does return originating evidence, but its dataset is separate from the fresh dataset generated by "Generate & evaluate." No fake evaluation history or derived confidence score.
7. **Readiness checks are narrow.** Health probes do not establish model, provider or vector-index health.
8. **State retention.** Query text/results and evaluation reports are kept in memory for this tab session, not written to local storage. Only upload receipts (including filename metadata) persist locally. There is no server-side document inventory or frontend user/org concept.

## Backend finding: output privacy integration

`services/guardrails.py::evaluate_output` returns `sanitized_text`, but `services/query_pipeline.py` returns and stores the original `answer`. Its public schema exposes only the privacy flags, not sanitized output. The UI suppresses answer text when `guardrails.output.safe` is false. This is a display safeguard only: the original answer still crosses the network and is saved by the backend. Fixing that fully requires a separate backend change to use the sanitized answer consistently and re-evaluate citation/validation semantics as needed. The backend is unchanged in this deliverable, per the feature-freeze instruction.

Generated evaluation reports do not expose output guardrail flags, so the UI cannot apply the same flag-based suppression to their returned answer fields. Local email redaction is explicitly a demonstration only.

## Validation

```powershell
npm ci
npx playwright install chromium
npm test
npm run build
```

Browser tests stub API responses solely inside the test runner and verify route empty states, no automatic evaluation calls, multipart upload, citation/trace navigation, structured 400/429/502/503 handling, unsafe output suppression, zero-case evaluations, degraded readiness and mobile/reduced-motion behavior. They do not certify a running backend deployment.

No live database, Redis, embedding/reranker models, provider keys or original backend `.env` were supplied in the ZIP, so live end-to-end ingestion, generation and evaluation must be verified against your existing backend. No LLM tokens are consumed by frontend tests or Evi.

## Files outside frontend

None modified. The backend, Docker Compose, root README and root `.gitignore` retain their original bytes. The ZIP is an additive frontend-only package. Dependencies, generated output, secrets, virtual environments and upload directories are excluded. Run `npm ci` to restore frontend dependencies.

## Verification record

The production TypeScript/Vite build passed. Fourteen browser contract checks passed across the verification runs, including the mobile layout fix and in-flight navigation. Desktop landing, Ask, Knowledge and Evaluations plus mobile Ask were visually reviewed. Browser tests used synthetic responses isolated to tests; no live backend or LLM evaluations were run.
