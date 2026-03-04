"""
RAG (Retrieval-Augmented Generation) module for investment presentation data.

Usage:
    1. Build index:  cd RAG && python3 build_index.py
    2. Query:        cd RAG && python3 query.py
    3. Programmatic:
        from RAG.rag_engine import RAGEngine
        engine = RAGEngine(index_path="RAG/index")
        result = engine.query("What are the company's key products?")
"""
