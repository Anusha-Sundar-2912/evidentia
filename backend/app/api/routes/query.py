from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.query import (
    AskRequest,
    AskResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.query_pipeline import (
    run_query_pipeline,
)
from app.services.rag import (
    bm25_search,
    hybrid_search,
    semantic_search,
)


router = APIRouter()


def get_filters(request) -> dict | None:
    if request.filters is None:
        return None

    return request.filters.model_dump(
        exclude_none=True
    )


@router.post(
    "/search/semantic",
    response_model=SearchResponse,
)
def search_semantic(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    filters = get_filters(request)

    results = semantic_search(
        db=db,
        query=request.query,
        top_k=request.top_k,
        filters=filters,
    )

    return {
        "query": request.query,
        "mode": "semantic",
        "results": results,
    }


@router.post(
    "/search/bm25",
    response_model=SearchResponse,
)
def search_bm25(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    filters = get_filters(request)

    results = bm25_search(
        db=db,
        query=request.query,
        top_k=request.top_k,
        filters=filters,
    )

    return {
        "query": request.query,
        "mode": "bm25",
        "results": results,
    }


@router.post(
    "/search/hybrid",
    response_model=SearchResponse,
)
def search_hybrid(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    filters = get_filters(request)

    results = hybrid_search(
        db=db,
        query=request.query,
        top_k=request.top_k,
        filters=filters,
    )

    return {
        "query": request.query,
        "mode": "hybrid",
        "results": results,
    }


@router.post(
    "/ask",
    response_model=AskResponse,
)
def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db),
):
    filters = get_filters(
        request
    )

    return run_query_pipeline(
        db=db,
        query=request.query,
        top_k=request.top_k,
        filters=filters,
        conversation_id=(
            request.conversation_id
        ),
    )