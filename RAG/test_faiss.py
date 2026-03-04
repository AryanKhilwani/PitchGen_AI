"""Quick smoke test for FAISS-backed VectorStore."""

import sys, os

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from vector_store import VectorStore

store = VectorStore()
docs = [
    {
        "text": f"document {i} about topic {i%3}",
        "metadata": {"source": "test", "section": f"sec{i}"},
    }
    for i in range(50)
]
embeds = np.random.randn(50, 384).astype(np.float32)
store.add(docs, embeds)

q = np.random.randn(384).astype(np.float32)

# Hybrid search
results = store.hybrid_search(q, query_text="document topic", top_k=5)
print(f"Hybrid search: {len(results)} results, top score: {results[0]['score']:.3f}")

# Filtered search
results2 = store.search(q, top_k=3, filter_fn=lambda m: m["section"] == "sec1")
print(f"Filtered search: {len(results2)} results")

# Metadata search
results3 = store.search_by_metadata(source="test")
print(f"Metadata search: {len(results3)} results")

# Save / load round-trip
store.save("/tmp/test_faiss_idx")
store2 = VectorStore()
store2.load("/tmp/test_faiss_idx")
results4 = store2.hybrid_search(q, query_text="document topic", top_k=5)
print(f"After reload: {len(results4)} results")

print("\nALL TESTS PASSED")
