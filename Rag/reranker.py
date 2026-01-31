from sentence_transformers import CrossEncoder

cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(query: str, docs: list[dict], top_k=5):
    """
    docs: [{ "text": ..., "metadata": ... }]
    """
    pairs = [(query, d["text"]) for d in docs]
    scores = cross_encoder.predict(pairs)

    ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)

    return [doc for _, doc in ranked[:top_k]]
