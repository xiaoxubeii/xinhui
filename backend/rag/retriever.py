# -*- coding: utf-8 -*-
"""
Knowledge retriever for querying the vector database.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False


class RetrievalResult:
    """A single retrieval result."""

    def __init__(
        self,
        content: str,
        source: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.content = content
        self.source = source
        self.score = score
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "score": self.score,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"RetrievalResult(score={self.score:.3f}, source={self.source})"


class KnowledgeRetriever:
    """Retrieve relevant knowledge from vector database."""

    def __init__(
        self,
        persist_directory: str | Path,
        collection_name: str = "cpet_knowledge",
    ):
        if not HAS_CHROMA:
            raise ImportError("chromadb is required. Install with: pip install chromadb")

        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get collection (will raise if not exists)
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except Exception:
            # Create empty collection if not exists
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "CPET clinical knowledge base"},
            )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: The search query
            top_k: Maximum number of results to return
            score_threshold: Minimum similarity score (0-1, higher is more similar)
            filter_metadata: Optional metadata filters

        Returns:
            List of RetrievalResult objects sorted by relevance
        """
        if self.collection.count() == 0:
            return []

        # Build query parameters
        query_params = {
            "query_texts": [query],
            "n_results": top_k,
        }

        if filter_metadata:
            query_params["where"] = filter_metadata

        # Execute query
        results = self.collection.query(**query_params)

        # Process results
        retrieval_results = []

        if results and results["documents"] and results["documents"][0]:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(documents)
            distances = results["distances"][0] if results["distances"] else [0.0] * len(documents)

            for doc, meta, dist in zip(documents, metadatas, distances):
                # Convert distance to similarity score (ChromaDB uses L2 distance by default)
                # Lower distance = higher similarity
                # We normalize to 0-1 range where 1 is most similar
                score = 1.0 / (1.0 + dist)

                if score >= score_threshold:
                    source = meta.pop("source", "unknown") if meta else "unknown"
                    result = RetrievalResult(
                        content=doc,
                        source=source,
                        score=score,
                        metadata=meta,
                    )
                    retrieval_results.append(result)

        return retrieval_results

    def retrieve_with_context(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        max_context_length: int = 2000,
    ) -> str:
        """
        Retrieve and format results as context string for LLM.

        Args:
            query: The search query
            top_k: Maximum number of results
            score_threshold: Minimum similarity score
            max_context_length: Maximum total context length

        Returns:
            Formatted context string
        """
        results = self.retrieve(query, top_k, score_threshold)

        if not results:
            return ""

        context_parts = []
        total_length = 0

        for i, result in enumerate(results, 1):
            # Format each result
            title = result.metadata.get("title", "未知来源")
            part = f"[参考{i}] {title}\n{result.content}\n"

            if total_length + len(part) > max_context_length:
                # Truncate if exceeds limit
                remaining = max_context_length - total_length
                if remaining > 100:
                    part = part[:remaining] + "..."
                    context_parts.append(part)
                break

            context_parts.append(part)
            total_length += len(part)

        return "\n".join(context_parts)

    def is_ready(self) -> bool:
        """Check if the retriever has indexed documents."""
        return self.collection.count() > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            "collection_name": self.collection_name,
            "document_count": self.collection.count(),
            "persist_directory": str(self.persist_directory),
            "ready": self.is_ready(),
        }
