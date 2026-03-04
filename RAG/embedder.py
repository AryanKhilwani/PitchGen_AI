"""
Embedder Module
Creates embeddings using a local sentence-transformers model (all-MiniLM-L6-v2).
Runs entirely offline — no API calls, no rate limits, no cost.
Model is ~80MB and produces 384-dim embeddings.
"""

import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer

# Small, fast model — based on MiniLM (distilled from RoBERTa-like architecture)
# 384-dim embeddings, ~80MB download, runs on CPU in seconds
MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 64

# Lazy-loaded singleton so the model is only loaded once
_model = None


def _get_model() -> SentenceTransformer:
    """Load model on first use (cached for subsequent calls)."""
    global _model
    if _model is None:
        print(f"Loading embedding model: {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
        print(f"Model loaded (dim={_model.get_sentence_embedding_dimension()})")
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Embed a list of texts locally.
    Returns numpy array of shape (n_texts, 384).
    """
    model = _get_model()
    print(f"  Embedding {len(texts)} texts (batch_size={BATCH_SIZE})...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # pre-normalize for cosine similarity
    )
    return np.array(embeddings, dtype=np.float32)


def embed_query(query: str) -> np.ndarray:
    """
    Embed a single query string for retrieval.
    Returns numpy array of shape (384,).
    """
    model = _get_model()
    embedding = model.encode(
        query,
        normalize_embeddings=True,
    )
    return np.array(embedding, dtype=np.float32)
