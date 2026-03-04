"""
Build Index
One-time script to load data, create embeddings, and save the vector index.
Run this whenever the source data changes.

Usage: python3 build_index.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from knowledge_base import build_knowledge_base
from embedder import embed_texts
from vector_store import VectorStore


INDEX_PATH = "index"

# Paths relative to this script's location (RAG/)
PUBLIC_DATA = "../Public_data_cleaner/outputs/final_structured_data.json"
PRIVATE_DATA = "../Private_data_extractor/outputs/private_data_bundle.json"


def main():
    print("=" * 60)
    print("Building Knowledge Base Index")
    print("=" * 60)

    # Step 1: Load and flatten documents
    documents = build_knowledge_base(
        public_data_path=PUBLIC_DATA,
        private_data_path=PRIVATE_DATA,
    )

    if not documents:
        print("No documents found. Exiting.")
        return

    # Step 2: Create embeddings
    print(f"\nCreating embeddings for {len(documents)} documents...")
    texts = [doc["text"] for doc in documents]
    embeddings = embed_texts(texts)
    print(f"Embeddings shape: {embeddings.shape}")

    # Step 3: Build and save vector store
    store = VectorStore()
    store.add(documents, embeddings)
    store.save(INDEX_PATH)

    print("\n" + "=" * 60)
    print(f"Index built successfully! ({len(documents)} documents indexed)")
    print(f"Saved to: {INDEX_PATH}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
