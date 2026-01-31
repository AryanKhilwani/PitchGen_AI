from sentence_transformers import SentenceTransformer

# Load once at module import (important for speed)
_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings using a local SentenceTransformer model.
    Free, fast, and suitable for RAG.
    """
    embeddings = _model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,  # improves cosine similarity
    )
    return embeddings.tolist()
