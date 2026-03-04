"""
Query Interface
Interactive CLI to query the RAG knowledge base.
Also supports single-shot queries and presentation-mode retrieval.

Usage:
  Interactive:   python3 query.py
  Single query:  python3 query.py "What products does Kalyani Forge manufacture?"
  Presentation:  python3 query.py --presentation
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from rag_engine import RAGEngine, retrieve_for_presentation


INDEX_PATH = "index"


def interactive_mode(engine: RAGEngine):
    """Interactive query loop."""
    print("\n" + "=" * 60)
    print("RAG Knowledge Base - Interactive Query")
    print("Type 'quit' to exit, 'sources' to toggle source display")
    print("=" * 60)

    show_sources = True

    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break
        if question.lower() == "sources":
            show_sources = not show_sources
            print(f"Source display: {'ON' if show_sources else 'OFF'}")
            continue

        print("\nSearching knowledge base...")
        result = engine.query(question, top_k=10)

        print("\n" + "-" * 40)
        print(result["answer"])
        print("-" * 40)

        if show_sources and result["sources"]:
            print(f"\nSources ({len(result['sources'])} documents):")
            for s in result["sources"][:5]:
                src_label = f"[{s['source']}]" if s["source"] else ""
                cat_label = s.get("category", "")
                print(
                    f"  {src_label} {cat_label} > {s['section']} (score: {s['score']})"
                )


def presentation_mode(engine: RAGEngine):
    """Retrieve data for all presentation sections and save to JSON."""
    section_data = retrieve_for_presentation(engine, top_k=8)

    # Convert to serializable format
    output = {}
    for section_key, results in section_data.items():
        output[section_key] = {
            "documents": [
                {"text": r["text"], "score": r["score"], "metadata": r["metadata"]}
                for r in results
            ],
            "count": len(results),
        }

    output_path = "outputs/presentation_context.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nPresentation context saved to {output_path}")
    print(f"Sections retrieved: {len(output)}")
    for key, val in output.items():
        print(f"  {key}: {val['count']} documents")


def single_query(engine: RAGEngine, question: str):
    """Run a single query and print the result."""
    print(f"Query: {question}\n")
    print("Searching knowledge base...")

    result = engine.query(question, top_k=10)

    print("\n" + "=" * 60)
    print(result["answer"])
    print("=" * 60)

    if result["sources"]:
        print(f"\nSources ({len(result['sources'])} documents):")
        for s in result["sources"][:5]:
            src_label = f"[{s['source']}]" if s["source"] else ""
            cat_label = s.get("category", "")
            print(f"  {src_label} {cat_label} > {s['section']} (score: {s['score']})")


def main():
    engine = RAGEngine(index_path=INDEX_PATH)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--presentation":
            presentation_mode(engine)
        else:
            # Single query mode
            question = " ".join(sys.argv[1:])
            single_query(engine, question)
    else:
        interactive_mode(engine)


if __name__ == "__main__":
    main()
