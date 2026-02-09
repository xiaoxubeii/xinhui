# -*- coding: utf-8 -*-
"""
RAG API endpoints for knowledge base management.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/rag", tags=["RAG"])

# Default paths
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "vector_db"
DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parent.parent.parent / "knowledge"


class IndexRequest(BaseModel):
    source: str = Field(..., description="File or directory path to index")
    recursive: bool = Field(True, description="Recursively index subdirectories")


class IndexResponse(BaseModel):
    indexed_count: int
    total_documents: int
    source: str


class QueryRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    score_threshold: float = Field(0.0, ge=0.0, le=1.0, description="Minimum score")


class RetrievalResultItem(BaseModel):
    content: str
    source: str
    score: float
    title: Optional[str] = None


class QueryResponse(BaseModel):
    query: str
    results: List[RetrievalResultItem]
    context: str


class StatsResponse(BaseModel):
    collection_name: str
    document_count: int
    persist_directory: str
    ready: bool


def _get_indexer():
    """Get knowledge indexer instance."""
    try:
        from ..rag import KnowledgeIndexer
        return KnowledgeIndexer(DEFAULT_DB_PATH)
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG module not available: {e}. Install chromadb: pip install chromadb"
        )


def _get_retriever():
    """Get knowledge retriever instance."""
    try:
        from ..rag import KnowledgeRetriever
        return KnowledgeRetriever(DEFAULT_DB_PATH)
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG module not available: {e}. Install chromadb: pip install chromadb"
        )


@router.post("/index", response_model=IndexResponse)
def index_documents(request: IndexRequest):
    """Index documents into the knowledge base."""
    indexer = _get_indexer()
    source_path = Path(request.source)

    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"Source not found: {request.source}")

    if source_path.is_file():
        count = indexer.index_file(source_path)
    else:
        count = indexer.index_directory(source_path, recursive=request.recursive)

    stats = indexer.get_stats()

    return IndexResponse(
        indexed_count=count,
        total_documents=stats["document_count"],
        source=str(source_path),
    )


@router.post("/index/default", response_model=IndexResponse)
def index_default_knowledge():
    """Index the default knowledge directory."""
    if not DEFAULT_KNOWLEDGE_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Default knowledge directory not found: {DEFAULT_KNOWLEDGE_PATH}"
        )

    indexer = _get_indexer()
    count = indexer.index_directory(DEFAULT_KNOWLEDGE_PATH, recursive=True)
    stats = indexer.get_stats()

    return IndexResponse(
        indexed_count=count,
        total_documents=stats["document_count"],
        source=str(DEFAULT_KNOWLEDGE_PATH),
    )


@router.post("/query", response_model=QueryResponse)
def query_knowledge(request: QueryRequest):
    """Query the knowledge base."""
    retriever = _get_retriever()

    if not retriever.is_ready():
        raise HTTPException(
            status_code=400,
            detail="Knowledge base is empty. Index documents first."
        )

    results = retriever.retrieve(
        request.query,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
    )

    context = retriever.retrieve_with_context(
        request.query,
        top_k=request.top_k,
    )

    return QueryResponse(
        query=request.query,
        results=[
            RetrievalResultItem(
                content=r.content,
                source=r.source,
                score=r.score,
                title=r.metadata.get("title"),
            )
            for r in results
        ],
        context=context,
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get knowledge base statistics."""
    retriever = _get_retriever()
    stats = retriever.get_stats()

    return StatsResponse(
        collection_name=stats["collection_name"],
        document_count=stats["document_count"],
        persist_directory=stats["persist_directory"],
        ready=stats["ready"],
    )


@router.delete("/clear")
def clear_knowledge():
    """Clear all documents from the knowledge base."""
    indexer = _get_indexer()
    indexer.clear()
    return {"message": "Knowledge base cleared", "document_count": 0}
