"""
Vector Store – FAISS-backed hybrid retrieval
=============================================
Semantic search via FAISS (inner-product index) + keyword scoring via BM25.
Supports metadata filtering and persists to disk.

Index strategy (auto-selected):
  • < IVF_THRESHOLD docs  → IndexFlatIP   (exact, O(n) but BLAS-optimized)
  • ≥ IVF_THRESHOLD docs  → IndexIVFFlat  (approximate, sub-linear via clustering)
"""

import os
import math
import pickle
import re
import numpy as np
import faiss
from collections import Counter
from typing import List, Dict, Optional, Callable

# When the doc count reaches this, switch from flat to IVF index
IVF_THRESHOLD = 10_000
# Number of clusters for IVF (sqrt(n) is auto-calculated, this is the min)
MIN_IVF_NLIST = 16
# How many clusters to probe at query time (higher = more accurate, slower)
IVF_NPROBE = 10


# ======================================================================
# BM25 keyword index (unchanged)
# ======================================================================


class BM25:
    """Lightweight BM25 keyword index built over document texts."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lens: List[int] = []
        self.avg_dl: float = 0
        self.tf_cache: List[Dict[str, int]] = []
        self.n_docs: int = 0

    def fit(self, texts: List[str]):
        """Build the BM25 index from a list of document texts."""
        self.n_docs = len(texts)
        self.doc_freqs = {}
        self.doc_lens = []
        self.tf_cache = []

        for text in texts:
            tokens = self._tokenize(text)
            self.doc_lens.append(len(tokens))
            tf = Counter(tokens)
            self.tf_cache.append(tf)
            for term in tf:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avg_dl = sum(self.doc_lens) / max(self.n_docs, 1)

    def score(self, query: str, doc_indices: Optional[List[int]] = None) -> np.ndarray:
        """Score all (or selected) documents against a query."""
        query_tokens = self._tokenize(query)
        n = self.n_docs if doc_indices is None else len(doc_indices)
        scores = np.zeros(n, dtype=np.float32)

        indices = doc_indices if doc_indices is not None else range(self.n_docs)

        for i, idx in enumerate(indices):
            tf = self.tf_cache[idx]
            dl = self.doc_lens[idx]

            for term in query_tokens:
                if term not in tf:
                    continue
                term_tf = tf[term]
                df = self.doc_freqs.get(term, 0)
                idf = math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1)
                numerator = term_tf * (self.k1 + 1)
                denominator = term_tf + self.k1 * (
                    1 - self.b + self.b * dl / self.avg_dl
                )
                scores[i] += idf * numerator / denominator

        return scores

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace + punctuation tokenizer, lowercased."""
        return re.findall(r"[a-z0-9]+", text.lower())


# ======================================================================
# FAISS-backed VectorStore
# ======================================================================


class VectorStore:
    def __init__(self):
        self.embeddings: Optional[np.ndarray] = None  # (n, dim) float32
        self.documents: List[Dict] = []  # [{"text": ..., "metadata": ...}]
        self.bm25: Optional[BM25] = None
        self.faiss_index: Optional[faiss.Index] = None
        self._dim: int = 0  # embedding dimension

    # ------------------------------------------------------------------
    # FAISS index management
    # ------------------------------------------------------------------

    def _build_faiss_index(self):
        """Build or rebuild the FAISS index from self.embeddings."""
        if self.embeddings is None or len(self.embeddings) == 0:
            self.faiss_index = None
            return

        n, dim = self.embeddings.shape
        self._dim = dim

        # Ensure float32 and L2-normalised (so Inner Product = cosine sim)
        vecs = np.ascontiguousarray(self.embeddings, dtype=np.float32)
        faiss.normalize_L2(vecs)

        if n < IVF_THRESHOLD:
            # Exact search – still BLAS-accelerated, ~10-50× faster than numpy
            self.faiss_index = faiss.IndexFlatIP(dim)
            self.faiss_index.add(vecs)
            index_type = "Flat (exact)"
        else:
            # Approximate search – IVF with inner product
            nlist = max(MIN_IVF_NLIST, int(math.sqrt(n)))
            quantizer = faiss.IndexFlatIP(dim)
            self.faiss_index = faiss.IndexIVFFlat(
                quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT
            )
            self.faiss_index.train(vecs)
            self.faiss_index.add(vecs)
            self.faiss_index.nprobe = IVF_NPROBE
            index_type = f"IVF (nlist={nlist}, nprobe={IVF_NPROBE})"

        print(f"  FAISS index built: {index_type}, {n} vectors, dim={dim}")

    # ------------------------------------------------------------------
    # Public API (fully backward-compatible)
    # ------------------------------------------------------------------

    def add(self, documents: List[Dict], embeddings: np.ndarray):
        """Add documents and their embeddings to the store."""
        if self.embeddings is None:
            self.embeddings = embeddings.astype(np.float32)
            self.documents = documents
        else:
            self.embeddings = np.vstack(
                [self.embeddings, embeddings.astype(np.float32)]
            )
            self.documents.extend(documents)

        self._build_faiss_index()
        self._build_bm25()

    def _build_bm25(self):
        """Build/rebuild the BM25 keyword index."""
        self.bm25 = BM25()
        texts = [doc["text"] for doc in self.documents]
        self.bm25.fit(texts)

    # ------------------------------------------------------------------
    # Search methods
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        min_score: float = 0.0,
        filter_fn: Optional[Callable[[Dict], bool]] = None,
    ) -> List[Dict]:
        """Semantic-only search (backward compatible)."""
        return self.hybrid_search(
            query_embedding=query_embedding,
            query_text=None,
            top_k=top_k,
            min_score=min_score,
            filter_fn=filter_fn,
            semantic_weight=1.0,
            keyword_weight=0.0,
        )

    def hybrid_search(
        self,
        query_embedding: np.ndarray,
        query_text: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.0,
        filter_fn: Optional[Callable[[Dict], bool]] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> List[Dict]:
        """
        Hybrid search: FAISS semantic similarity + BM25 keyword matching.

        When a metadata filter_fn is provided, we fall back to a filtered
        subset search (still FAISS-accelerated on the subset).
        """
        if self.faiss_index is None or len(self.documents) == 0:
            return []

        # --- Step 1: Pre-filter by metadata if needed ---
        if filter_fn is not None:
            candidate_indices = [
                i for i, doc in enumerate(self.documents) if filter_fn(doc["metadata"])
            ]
            if not candidate_indices:
                return []
            return self._search_subset(
                candidate_indices,
                query_embedding,
                query_text,
                top_k,
                min_score,
                semantic_weight,
                keyword_weight,
            )

        # --- Step 2: Full-corpus FAISS search ---
        query_vec = np.ascontiguousarray(
            query_embedding.reshape(1, -1), dtype=np.float32
        )
        faiss.normalize_L2(query_vec)

        # Over-retrieve so we have enough after BM25 re-ranking
        fetch_k = min(top_k * 3, len(self.documents))
        distances, indices = self.faiss_index.search(query_vec, fetch_k)
        distances = distances[0]  # shape (fetch_k,)
        indices = indices[0]

        # Filter out any -1 entries (padding from FAISS)
        valid = indices >= 0
        distances = distances[valid]
        indices = indices[valid]

        if len(indices) == 0:
            return []

        # Normalize semantic scores to [0, 1]
        s_min, s_max = distances.min(), distances.max()
        if s_max > s_min:
            sem_norm = (distances - s_min) / (s_max - s_min)
        else:
            sem_norm = np.ones_like(distances)

        # --- Step 3: BM25 keyword scores ---
        if query_text and self.bm25 and keyword_weight > 0:
            bm25_scores = self.bm25.score(query_text, doc_indices=indices.tolist())
            b_min, b_max = bm25_scores.min(), bm25_scores.max()
            if b_max > b_min:
                bm25_norm = (bm25_scores - b_min) / (b_max - b_min)
            else:
                bm25_norm = np.zeros_like(bm25_scores)
        else:
            bm25_norm = np.zeros_like(sem_norm)

        # --- Step 4: Combine & rank ---
        combined = semantic_weight * sem_norm + keyword_weight * bm25_norm
        order = np.argsort(combined)[::-1]

        results = []
        for pos in order:
            score = float(combined[pos])
            if score < min_score:
                continue
            idx = int(indices[pos])
            results.append(
                {
                    "text": self.documents[idx]["text"],
                    "metadata": self.documents[idx]["metadata"],
                    "score": score,
                    "semantic_score": float(distances[pos]),
                    "keyword_score": float(bm25_norm[pos]) if query_text else 0.0,
                }
            )
            if len(results) >= top_k:
                break

        return results

    def _search_subset(
        self,
        candidate_indices: List[int],
        query_embedding: np.ndarray,
        query_text: Optional[str],
        top_k: int,
        min_score: float,
        semantic_weight: float,
        keyword_weight: float,
    ) -> List[Dict]:
        """
        Filtered search over a subset of documents.
        Builds a temporary FAISS index for the filtered candidates.
        """
        subset_embeddings = self.embeddings[candidate_indices].astype(np.float32)
        subset_embeddings = np.ascontiguousarray(subset_embeddings)
        faiss.normalize_L2(subset_embeddings)

        dim = subset_embeddings.shape[1]
        tmp_index = faiss.IndexFlatIP(dim)
        tmp_index.add(subset_embeddings)

        query_vec = np.ascontiguousarray(
            query_embedding.reshape(1, -1), dtype=np.float32
        )
        faiss.normalize_L2(query_vec)

        fetch_k = min(top_k * 3, len(candidate_indices))
        distances, local_indices = tmp_index.search(query_vec, fetch_k)
        distances = distances[0]
        local_indices = local_indices[0]

        valid = local_indices >= 0
        distances = distances[valid]
        local_indices = local_indices[valid]

        if len(local_indices) == 0:
            return []

        # Map back to global indices
        global_indices = [candidate_indices[li] for li in local_indices]

        # Normalize semantic
        s_min, s_max = distances.min(), distances.max()
        if s_max > s_min:
            sem_norm = (distances - s_min) / (s_max - s_min)
        else:
            sem_norm = np.ones_like(distances)

        # BM25
        if query_text and self.bm25 and keyword_weight > 0:
            bm25_scores = self.bm25.score(query_text, doc_indices=global_indices)
            b_min, b_max = bm25_scores.min(), bm25_scores.max()
            if b_max > b_min:
                bm25_norm = (bm25_scores - b_min) / (b_max - b_min)
            else:
                bm25_norm = np.zeros_like(bm25_scores)
        else:
            bm25_norm = np.zeros_like(sem_norm)

        combined = semantic_weight * sem_norm + keyword_weight * bm25_norm
        order = np.argsort(combined)[::-1]

        results = []
        for pos in order:
            score = float(combined[pos])
            if score < min_score:
                continue
            gidx = global_indices[pos]
            results.append(
                {
                    "text": self.documents[gidx]["text"],
                    "metadata": self.documents[gidx]["metadata"],
                    "score": score,
                    "semantic_score": float(distances[pos]),
                    "keyword_score": float(bm25_norm[pos]) if query_text else 0.0,
                }
            )
            if len(results) >= top_k:
                break

        return results

    def search_by_metadata(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
        section: Optional[str] = None,
    ) -> List[Dict]:
        """Direct metadata lookup — no embedding search."""
        results = []
        for doc in self.documents:
            meta = doc["metadata"]
            if source and meta.get("source") != source:
                continue
            if category and meta.get("category", "").lower() != category.lower():
                continue
            if section and section.lower() not in meta.get("section", "").lower():
                continue
            results.append(doc)
        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str = "index"):
        """Save the vector store to disk (embeddings as npy, docs as pickle)."""
        os.makedirs(path, exist_ok=True)

        np.save(os.path.join(path, "embeddings.npy"), self.embeddings)
        with open(os.path.join(path, "documents.pkl"), "wb") as f:
            pickle.dump(self.documents, f)

        print(f"Vector store saved to {path}/ ({len(self.documents)} documents)")

    def load(self, path: str = "index") -> bool:
        """Load the vector store from disk. Returns True if successful."""
        emb_path = os.path.join(path, "embeddings.npy")
        doc_path = os.path.join(path, "documents.pkl")

        if not os.path.exists(emb_path) or not os.path.exists(doc_path):
            return False

        self.embeddings = np.load(emb_path).astype(np.float32)
        with open(doc_path, "rb") as f:
            self.documents = pickle.load(f)

        # Rebuild indexes on load
        self._build_faiss_index()
        self._build_bm25()

        print(
            f"Vector store loaded from {path}/ ({len(self.documents)} documents, dim={self.embeddings.shape[1]})"
        )
        return True

    def __len__(self):
        return len(self.documents)
