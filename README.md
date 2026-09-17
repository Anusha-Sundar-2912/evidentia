# Evidentia

### Enterprise Knowledge Intelligence with Evidence-Backed RAG

Evidentia is a governed enterprise knowledge intelligence platform designed to make Retrieval-Augmented Generation more transparent, measurable, and trustworthy.

Instead of treating RAG as a black box, Evidentia exposes the evidence behind generated answers. Users can ingest their own documents, ask questions against that knowledge, inspect citations and retrieval traces, analyze guardrail behavior, and evaluate the production RAG pipeline against automatically generated test cases.

> **Every answer should be backed by evidence.**

---

## Why Evidentia?

Connecting an LLM to documents does not automatically make its answers reliable.

Enterprise RAG systems must answer additional questions:

- Was the correct evidence retrieved?
- Which passages influenced the answer?
- Are the generated claims actually supported?
- Are citations valid?
- How did semantic and lexical retrieval contribute?
- Did reranking improve evidence selection?
- Is sensitive information being handled safely?
- How well does the system perform on the organization's own knowledge?

Evidentia treats these as first-class parts of the product rather than hiding them behind a chat interface.

---

## Core Capabilities

### Knowledge Ingestion

Evidentia accepts PDF and DOCX documents and processes them through an ingestion pipeline:

```text
Document
   ↓
Parsing
   ↓
Sentence-aware chunking
   ↓
Metadata extraction
   ↓
SentenceTransformer embeddings
   ↓
PostgreSQL + pgvector
   ↓
HNSW vector index
```

Uploaded files are used during ingestion and are not required for retrieval after their parsed chunks, metadata, and embeddings have been persisted.

### Hybrid Retrieval

Evidentia combines dense and lexical retrieval instead of relying on a single search strategy.

The retrieval pipeline includes:

- SentenceTransformer embeddings
- PostgreSQL + pgvector vector search
- HNSW cosine-similarity index
- BM25 lexical retrieval
- Reciprocal Rank Fusion
- multi-query retrieval
- query rewriting and decomposition
- metadata filtering
- cross-encoder reranking
- contextual evidence compression

The HNSW index is configured for cosine similarity over 384-dimensional embeddings.

### Evidence-Grounded Generation

Retrieved passages are compressed into a focused evidence set before generation.

The generation layer is instructed to answer from supplied evidence and supports:

- inline citations
- source attribution
- citation validation
- groundedness assessment
- refusal when sufficient evidence is unavailable
- structured provider error handling

The application distinguishes heuristic groundedness measurements from model confidence.

### Retrieval Trace

The Retrieval Lab exposes the path from question to evidence.

A trace can surface:

```text
Original query
   ↓
Query rewrite / decomposition
   ↓
Multi-query search
   ↓
Vector + BM25 retrieval
   ↓
Reciprocal Rank Fusion
   ↓
Cross-encoder reranking
   ↓
Selected evidence
   ↓
Context compression
   ↓
Grounded generation
   ↓
Citation validation
```

Stage timings and selected passages make the RAG pipeline inspectable rather than opaque.

### Guardrails

The query pipeline includes deterministic controls for:

- prompt-injection detection
- PII detection
- PII redaction
- input validation
- output sanitization
- citation validation
- groundedness checks
- refusal behavior

Supported PII patterns include common email, phone, Aadhaar, PAN, and IPv4 formats.

### Conversation Memory

Conversation context is maintained using Redis with bounded history and expiration.

Memory failures are handled defensively so that temporary Redis problems do not have to take down the core retrieval pipeline.

### Evaluation Lab

Evidentia can evaluate its production RAG system against knowledge derived from uploaded documents.

The evaluation pipeline can:

1. sample evidence from the knowledge base,
2. generate evaluation questions and reference answers,
3. preserve source chunks as hidden ground truth,
4. judge graded passage relevance,
5. execute the same production retrieval pipeline,
6. evaluate retrieval quality,
7. decompose generated answers into claims,
8. measure semantic support and citation quality.

Retrieval metrics include:

- Hit@K
- Precision@K
- Recall@K
- Mean Reciprocal Rank
- nDCG

Answer-level evaluation includes:

- semantic faithfulness
- citation correctness
- citation coverage

This allows Evidentia to test retrieval and answer quality against a customer's own knowledge rather than relying only on a static benchmark.

---

## Architecture

```text
                         ┌──────────────────────────┐
                         │      React Frontend      │
                         │  Ask / Knowledge / Labs  │
                         └────────────┬─────────────┘
                                      │
                                      │ REST
                                      ▼
                         ┌──────────────────────────┐
                         │       FastAPI API        │
                         └────────────┬─────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
                 ▼                    ▼                    ▼
        ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
        │   Guardrails   │   │ Query Pipeline │   │ Evaluation Lab │
        └────────────────┘   └───────┬────────┘   └────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             Vector Search         BM25        Query Expansion
                    │                │                │
                    └────────────┬───┴────────────────┘
                                 ▼
                         Reciprocal Rank Fusion
                                 │
                                 ▼
                         Cross-Encoder Reranker
                                 │
                                 ▼
                         Evidence Compression
                                 │
                                 ▼
                          Grounded Generation
                                 │
                                 ▼
                      Validation + Citations
                                 │
                  ┌──────────────┴──────────────┐
                  ▼                             ▼
        PostgreSQL + pgvector                 Redis
```

---

## Technology Stack

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy 2
- PostgreSQL
- pgvector
- Redis
- Sentence Transformers
- CrossEncoder reranking
- BM25
- Groq-hosted LLM inference
- PyMuPDF
- python-docx

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- TanStack Query
- React Router
- Playwright

### Infrastructure

- Docker Compose for local PostgreSQL/pgvector and Redis
- Render-compatible FastAPI deployment
- Vercel-compatible frontend deployment

---

## Repository Structure

```text
evidentia/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── evaluation/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── uploads/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── store/
│   │   ├── styles/
│   │   └── types/
│   └── tests/
│
├── docker-compose.yml
├── .python-version
└── README.md
```

---

## Local Development

### Prerequisites

Install:

- Python 3.11
- Node.js
- Docker Desktop

### Start PostgreSQL and Redis

From the repository root:

```bash
docker compose up -d
```

The local Compose configuration exposes:

```text
PostgreSQL: localhost:5433
Redis:      localhost:6379
```

The PostgreSQL image includes pgvector support.

### Backend Environment

Create:

```text
backend/.env
```

Configure the following values:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/evidentia
REDIS_URL=redis://localhost:6379/0
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
GROQ_API_KEY=your_server_side_api_key
LLM_MODEL=openai/gpt-oss-120b
CORS_ORIGINS=http://localhost:5173
```

Never expose provider credentials through Vite environment variables or commit `.env` files.

### Run the Backend

Windows PowerShell:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API is available at:

```text
http://localhost:8000
```

Interactive FastAPI documentation:

```text
http://localhost:8000/docs
```

### Run the Frontend

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The frontend is available at:

```text
http://localhost:5173
```

---

## Main API Surface

All application endpoints use the `/api/v1` prefix.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/documents/upload` | Parse, chunk, embed and index a document |
| POST | `/query/ask` | Execute the production evidence-grounded RAG pipeline |
| POST | `/query/search/semantic` | Inspect semantic retrieval |
| POST | `/query/search/bm25` | Inspect lexical retrieval |
| POST | `/query/search/hybrid` | Inspect hybrid retrieval |
| POST | `/evaluations/generate` | Generate evaluation cases from knowledge |
| POST | `/evaluations/run-generated` | Evaluate the production pipeline |
| GET | `/health` | Application liveness |
| GET | `/ready` | PostgreSQL and Redis readiness |

---

## Product Workspaces

The frontend is organized into dedicated operational workspaces:

**Ask** provides evidence-grounded answers, citations, sources, groundedness information, latency and retrieval traces.

**Knowledge** handles PDF/DOCX ingestion and confirmed browser-side upload receipts.

**Retrieval Lab** exposes retrieval paths, selected passages, reranking, compression and stage timings.

**Guardrails** surfaces prompt-injection handling, validation and PII-redaction behavior.

**Evaluations** generates and executes knowledge-grounded RAG evaluations and presents retrieval and answer-quality metrics.

**System** reports API and dependency readiness.

---

## Evaluation Philosophy

Evaluation metrics are diagnostic measurements, not scores that should be artificially optimized to 100%.

A retrieval system can retrieve the correct evidence while a generated answer still contains unsupported claims. Likewise, strong citation correctness does not imply perfect retrieval.

Evidentia therefore evaluates retrieval and generation separately and exposes the results rather than hiding poor cases.

---

## Security Notes

- API credentials are server-side environment variables.
- `.env` files are excluded from version control.
- Uploaded source files are treated as temporary ingestion artifacts.
- Prompt-injection detection is applied before retrieval.
- Supported PII patterns can be detected and redacted.
- Provider failures are converted into structured API errors.

Production deployments should additionally introduce application-level authentication and authorization before exposing private organizational knowledge to multiple users.

---

## Current Scope

Evidentia is an engineering project focused on evidence-backed RAG, retrieval observability, guardrails and evaluation.

Current boundaries include:

- PDF and DOCX ingestion
- no full document-management CRUD interface
- browser-side ingestion receipts rather than a persistent frontend document inventory
- deterministic PII patterns rather than a full DLP platform
- lexical groundedness as a heuristic signal alongside semantic evaluation
- no multi-tenant authentication layer

These boundaries are kept explicit so that the UI does not claim capabilities the backend does not implement.

---

## Deployment

The intended deployment topology is:

```text
Vercel
   │
   │ React application
   ▼
Render FastAPI service
   │
   ├── PostgreSQL + pgvector
   ├── Redis-compatible key-value service
   └── Server-side LLM provider
```

Production environment variables must be configured through the deployment platform rather than committed to this repository.

---

## Design Principle

> **Every answer should be backed by evidence.**

Evidentia is built around the idea that enterprise AI should not merely produce plausible answers. It should make the evidence behind those answers inspectable, traceable and measurable.