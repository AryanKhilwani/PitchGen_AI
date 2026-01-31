import json
from document_builder import build_documents
from embedder import embed_texts
from vector_store import VectorStore
from retriever import Retriever


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    # ---------- LOAD DATA ----------
    public_data = load_json("outputs/public_data_bundle.json")
    private_data = load_json("outputs/private_data_bundle.json")

    # ---------- BUILD DOCUMENTS ----------
    documents = build_documents(public_data, private_data)
    texts = [d["text"] for d in documents]
    metadatas = [d["metadata"] for d in documents]

    print(f"🔹 Total documents: {len(texts)}")

    # ---------- EMBED ----------
    embeddings = embed_texts(texts)
    dim = len(embeddings[0])

    # ---------- VECTOR STORE ----------
    store = VectorStore(dim)
    store.add(embeddings, metadatas)

    # ---------- RETRIEVER ----------
    retriever = Retriever(store)

    # ---------- TEST QUERY ----------
    query = "products of the company"
    results = retriever.retrieve(query, k=5)

    print("\n🔍 Retrieved Results:")
    for r in results:
        print(r)
