# -*- coding: utf-8 -*-
"""
CLI tool for managing the knowledge base.

Usage:
    python -m backend.rag.cli index <directory>
    python -m backend.rag.cli query <question>
    python -m backend.rag.cli stats
    python -m backend.rag.cli clear
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def get_default_db_path() -> Path:
    """Get default vector database path."""
    return Path(__file__).resolve().parent.parent.parent / "data" / "vector_db"


def cmd_index(args: argparse.Namespace) -> int:
    """Index documents into vector database."""
    from .indexer import KnowledgeIndexer

    db_path = Path(args.db_path) if args.db_path else get_default_db_path()
    source_path = Path(args.source)

    if not source_path.exists():
        print(f"Error: Source path not found: {source_path}")
        return 1

    print(f"Indexing from: {source_path}")
    print(f"Database path: {db_path}")

    indexer = KnowledgeIndexer(db_path)

    if source_path.is_file():
        count = indexer.index_file(source_path)
    else:
        count = indexer.index_directory(source_path, recursive=not args.no_recursive)

    print(f"Indexed {count} document chunks")
    stats = indexer.get_stats()
    print(f"Total documents in database: {stats['document_count']}")

    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Query the knowledge base."""
    from .retriever import KnowledgeRetriever

    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        print("Run 'index' command first to build the knowledge base.")
        return 1

    retriever = KnowledgeRetriever(db_path)

    if not retriever.is_ready():
        print("Warning: Knowledge base is empty.")
        return 1

    query = " ".join(args.query)
    print(f"Query: {query}")
    print("-" * 50)

    results = retriever.retrieve(query, top_k=args.top_k)

    if not results:
        print("No relevant documents found.")
        return 0

    for i, result in enumerate(results, 1):
        title = result.metadata.get("title", "Unknown")
        print(f"\n[{i}] {title} (score: {result.score:.3f})")
        print(f"    Source: {result.source}")
        print(f"    Content: {result.content[:200]}...")

    return 0


def cmd_context(args: argparse.Namespace) -> int:
    """Get formatted context for a query."""
    from .retriever import KnowledgeRetriever

    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        return 1

    retriever = KnowledgeRetriever(db_path)
    query = " ".join(args.query)

    context = retriever.retrieve_with_context(
        query,
        top_k=args.top_k,
        max_context_length=args.max_length,
    )

    if context:
        print(context)
    else:
        print("No relevant context found.")

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show knowledge base statistics."""
    from .retriever import KnowledgeRetriever

    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    if not db_path.exists():
        print(f"Database path: {db_path} (not created)")
        return 0

    retriever = KnowledgeRetriever(db_path)
    stats = retriever.get_stats()

    print(f"Collection: {stats['collection_name']}")
    print(f"Documents: {stats['document_count']}")
    print(f"Path: {stats['persist_directory']}")
    print(f"Ready: {stats['ready']}")

    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    """Clear the knowledge base."""
    from .indexer import KnowledgeIndexer

    db_path = Path(args.db_path) if args.db_path else get_default_db_path()

    if not db_path.exists():
        print("Database does not exist.")
        return 0

    if not args.yes:
        confirm = input("Are you sure you want to clear the knowledge base? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return 0

    indexer = KnowledgeIndexer(db_path)
    indexer.clear()
    print("Knowledge base cleared.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CPET Knowledge Base CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db-path",
        help="Path to vector database (default: data/vector_db)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # index command
    index_parser = subparsers.add_parser("index", help="Index documents")
    index_parser.add_argument("source", help="File or directory to index")
    index_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't recursively index subdirectories",
    )

    # query command
    query_parser = subparsers.add_parser("query", help="Query knowledge base")
    query_parser.add_argument("query", nargs="+", help="Search query")
    query_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results (default: 5)",
    )

    # context command
    context_parser = subparsers.add_parser("context", help="Get formatted context")
    context_parser.add_argument("query", nargs="+", help="Search query")
    context_parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of results (default: 3)",
    )
    context_parser.add_argument(
        "--max-length",
        type=int,
        default=2000,
        help="Max context length (default: 2000)",
    )

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    # clear command
    clear_parser = subparsers.add_parser("clear", help="Clear knowledge base")
    clear_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "index": cmd_index,
        "query": cmd_query,
        "context": cmd_context,
        "stats": cmd_stats,
        "clear": cmd_clear,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
