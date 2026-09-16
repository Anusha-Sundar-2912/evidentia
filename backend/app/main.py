from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.documents import (
    router as documents_router,
)
from app.api.routes.evaluations import (
    router as evaluations_router,
)
from app.api.routes.health import (
    router as health_router,
)
from app.api.routes.query import (
    router as query_router,
)
from app.core.database import Base, engine
from app.core.exceptions import (
    LLMProviderError,
    LLMRateLimitError,
    LLMUnavailableError,
)
from app.models import Chunk, Document
from app.services.embeddings import (
    get_embedding_model,
)
from app.services.reranker import (
    get_reranker,
)


# ---------------------------------------------------------
# Database tables
# ---------------------------------------------------------

Base.metadata.create_all(
    bind=engine
)


# ---------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Preload Evidentia's local ML models during startup.

    This moves SentenceTransformer and CrossEncoder
    initialization out of the first user request,
    preventing large cold-start retrieval latency.
    """

    print(
        "Evidentia: loading embedding model..."
    )

    get_embedding_model()

    print(
        "Evidentia: embedding model ready."
    )

    print(
        "Evidentia: loading reranker model..."
    )

    get_reranker()

    print(
        "Evidentia: reranker model ready."
    )

    print(
        "Evidentia: startup complete."
    )

    yield

    print(
        "Evidentia: shutting down."
    )


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="Evidentia API",
    description=(
        "Enterprise Knowledge Intelligence Engine"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Structured LLM provider error handling
# ---------------------------------------------------------

@app.exception_handler(
    LLMRateLimitError
)
async def llm_rate_limit_handler(
    request: Request,
    exc: LLMRateLimitError,
):
    """
    Convert provider rate-limit failures into a clean
    HTTP 429 response instead of exposing a generic 500.
    """

    return JSONResponse(
        status_code=429,
        content={
            "error": "llm_rate_limited",
            "message": exc.message,
            "retryable": True,
        },
    )


@app.exception_handler(
    LLMUnavailableError
)
async def llm_unavailable_handler(
    request: Request,
    exc: LLMUnavailableError,
):
    """
    Represent temporary provider/network outages as
    HTTP 503 Service Unavailable.
    """

    return JSONResponse(
        status_code=503,
        content={
            "error": "llm_unavailable",
            "message": exc.message,
            "retryable": True,
        },
    )


@app.exception_handler(
    LLMProviderError
)
async def llm_provider_error_handler(
    request: Request,
    exc: LLMProviderError,
):
    """
    Handle other upstream LLM failures without exposing
    provider-specific exception details.
    """

    return JSONResponse(
        status_code=502,
        content={
            "error": "llm_provider_error",
            "message": exc.message,
            "retryable": exc.retryable,
        },
    )


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------

app.include_router(
    health_router,
    prefix="/api/v1",
    tags=["System"],
)

app.include_router(
    documents_router,
    prefix="/api/v1/documents",
    tags=["Documents"],
)

app.include_router(
    query_router,
    prefix="/api/v1/query",
    tags=["Retrieval"],
)

app.include_router(
    evaluations_router,
    prefix="/api/v1/evaluations",
    tags=["Evaluations"],
)


# ---------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "Evidentia",
        "description": (
            "Enterprise Knowledge Intelligence"
        ),
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }