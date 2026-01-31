from embedder import embed_texts


class Retriever:
    def __init__(self, vector_store):
        self.store = vector_store

    def retrieve(self, query: str, k=6):
        embedding = embed_texts([query])[0]
        return self.store.search(embedding, k=k)
