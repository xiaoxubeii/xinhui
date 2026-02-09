# -*- coding: utf-8 -*-
"""
Knowledge indexer for building and managing the vector database.

Supports:
- Markdown files (.md)
- Text files (.txt)
- PDF files (.pdf) - requires pypdf
- JSON knowledge bases (.json)
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


class Document:
    """A document chunk with metadata."""

    def __init__(
        self,
        content: str,
        source: str,
        chunk_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.content = content
        self.source = source
        self.chunk_id = chunk_id
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "chunk_id": self.chunk_id,
            "metadata": self.metadata,
        }


class TextSplitter:
    """Split text into chunks with overlap."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", ".", " ", ""]

    def split(self, text: str) -> List[str]:
        """Split text into chunks."""
        chunks = self._split_recursive(text, self.separators)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using separators."""
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        # Find the best separator
        separator = separators[-1]
        for sep in separators:
            if sep in text:
                separator = sep
                break

        # Split by separator
        if separator:
            parts = text.split(separator)
        else:
            # Character-level split as fallback
            parts = [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]
            return parts

        # Merge small parts into chunks
        chunks = []
        current_chunk = ""

        for part in parts:
            part_with_sep = part + separator if separator else part

            if len(current_chunk) + len(part_with_sep) <= self.chunk_size:
                current_chunk += part_with_sep
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                if len(part_with_sep) > self.chunk_size:
                    # Recursively split large parts
                    remaining_seps = separators[separators.index(separator) + 1:] if separator in separators else separators[-1:]
                    sub_chunks = self._split_recursive(part, remaining_seps)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part_with_sep

        if current_chunk:
            chunks.append(current_chunk)

        # Add overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            overlapped = []
            for i, chunk in enumerate(chunks):
                if i > 0:
                    # Add end of previous chunk as prefix
                    prev_end = chunks[i - 1][-self.chunk_overlap:]
                    chunk = prev_end + chunk
                overlapped.append(chunk)
            return overlapped

        return chunks


class KnowledgeIndexer:
    """Index knowledge documents into vector database."""

    def __init__(
        self,
        persist_directory: str | Path,
        collection_name: str = "cpet_knowledge",
        embedding_model: str = "default",
    ):
        if not HAS_CHROMA:
            raise ImportError("chromadb is required. Install with: pip install chromadb")

        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name
        self.embedding_model = embedding_model

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "CPET clinical knowledge base"},
        )

        self.splitter = TextSplitter(chunk_size=500, chunk_overlap=50)

    def _generate_chunk_id(self, source: str, content: str, index: int) -> str:
        """Generate unique chunk ID."""
        hash_input = f"{source}:{index}:{content[:100]}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def _load_markdown(self, path: Path) -> List[Document]:
        """Load and split markdown file."""
        content = path.read_text(encoding="utf-8")

        # Extract title from first heading
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else path.stem

        chunks = self.splitter.split(content)
        documents = []

        for i, chunk in enumerate(chunks):
            doc = Document(
                content=chunk,
                source=str(path),
                chunk_id=self._generate_chunk_id(str(path), chunk, i),
                metadata={
                    "title": title,
                    "type": "markdown",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            documents.append(doc)

        return documents

    def _load_text(self, path: Path) -> List[Document]:
        """Load and split text file."""
        content = path.read_text(encoding="utf-8")
        chunks = self.splitter.split(content)
        documents = []

        for i, chunk in enumerate(chunks):
            doc = Document(
                content=chunk,
                source=str(path),
                chunk_id=self._generate_chunk_id(str(path), chunk, i),
                metadata={
                    "title": path.stem,
                    "type": "text",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            documents.append(doc)

        return documents

    def _load_pdf(self, path: Path) -> List[Document]:
        """Load and split PDF file."""
        if not HAS_PYPDF:
            raise ImportError("pypdf is required for PDF support. Install with: pip install pypdf")

        reader = PdfReader(path)
        full_text = ""

        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n\n"

        chunks = self.splitter.split(full_text)
        documents = []

        # Try to extract title from metadata or first line
        title = reader.metadata.get("/Title", "") if reader.metadata else ""
        if not title:
            title = path.stem

        for i, chunk in enumerate(chunks):
            doc = Document(
                content=chunk,
                source=str(path),
                chunk_id=self._generate_chunk_id(str(path), chunk, i),
                metadata={
                    "title": title,
                    "type": "pdf",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "page_count": len(reader.pages),
                },
            )
            documents.append(doc)

        return documents

    def _load_json(self, path: Path) -> List[Document]:
        """Load JSON knowledge base."""
        data = json.loads(path.read_text(encoding="utf-8"))
        documents = []

        # Support different JSON formats
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, dict) and "knowledge" in data:
            items = data["knowledge"]
        else:
            # Treat as single document
            items = [data]

        for i, item in enumerate(items):
            if isinstance(item, str):
                content = item
                title = f"Item {i + 1}"
                metadata = {}
            elif isinstance(item, dict):
                content = item.get("content", "") or item.get("text", "") or json.dumps(item, ensure_ascii=False)
                title = item.get("title", "") or item.get("name", "") or f"Item {i + 1}"
                metadata = {k: v for k, v in item.items() if k not in ("content", "text")}
            else:
                continue

            chunks = self.splitter.split(content)

            for j, chunk in enumerate(chunks):
                doc = Document(
                    content=chunk,
                    source=str(path),
                    chunk_id=self._generate_chunk_id(str(path), chunk, j),
                    metadata={
                        "title": title,
                        "type": "json",
                        "item_index": i,
                        "chunk_index": j,
                        **metadata,
                    },
                )
                documents.append(doc)

        return documents

    def load_file(self, path: str | Path) -> List[Document]:
        """Load a single file and return documents."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()

        if suffix == ".md":
            return self._load_markdown(path)
        elif suffix == ".txt":
            return self._load_text(path)
        elif suffix == ".pdf":
            return self._load_pdf(path)
        elif suffix == ".json":
            return self._load_json(path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def load_directory(self, directory: str | Path, recursive: bool = True) -> List[Document]:
        """Load all supported files from directory."""
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        documents = []
        patterns = ["*.md", "*.txt", "*.json"]
        if HAS_PYPDF:
            patterns.append("*.pdf")

        for pattern in patterns:
            if recursive:
                files = directory.rglob(pattern)
            else:
                files = directory.glob(pattern)

            for file_path in files:
                try:
                    docs = self.load_file(file_path)
                    documents.extend(docs)
                except Exception as e:
                    print(f"Warning: Failed to load {file_path}: {e}")

        return documents

    def index_documents(self, documents: List[Document]) -> int:
        """Index documents into vector database."""
        if not documents:
            return 0

        # Prepare data for ChromaDB
        ids = [doc.chunk_id for doc in documents]
        contents = [doc.content for doc in documents]
        metadatas = [
            {
                "source": doc.source,
                **{k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                   for k, v in doc.metadata.items()}
            }
            for doc in documents
        ]

        # Upsert to collection
        self.collection.upsert(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
        )

        return len(documents)

    def index_file(self, path: str | Path) -> int:
        """Load and index a single file."""
        documents = self.load_file(path)
        return self.index_documents(documents)

    def index_directory(self, directory: str | Path, recursive: bool = True) -> int:
        """Load and index all files from directory."""
        documents = self.load_directory(directory, recursive)
        return self.index_documents(documents)

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "collection_name": self.collection_name,
            "document_count": self.collection.count(),
            "persist_directory": str(self.persist_directory),
        }

    def clear(self) -> None:
        """Clear all documents from collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "CPET clinical knowledge base"},
        )
