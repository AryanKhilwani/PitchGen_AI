"""
RAG Engine
Multi-strategy retrieval with hybrid search (semantic + BM25),
multi-query fusion, and metadata filtering.
Combines retrieval with Gemini generation for investment analysis.
"""

import os
import re
import time
import json
from typing import List, Dict, Optional, Callable
from google import genai
from dotenv import load_dotenv
from vector_store import VectorStore
from embedder import embed_query, embed_texts

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Generation config
GENERATION_MODEL = "gemini-2.0-flash"
MAX_RETRIES = 10
API_CALL_DELAY = 3  # seconds between generation calls for free tier


class RAGEngine:
    def __init__(self, index_path: str = "index"):
        self.store = VectorStore()
        loaded = self.store.load(index_path)
        if not loaded:
            raise FileNotFoundError(
                f"No index found at '{index_path}/'. Run build_index.py first."
            )

    # ------------------------------------------------------------------
    # Retrieval strategies
    # ------------------------------------------------------------------

    def retrieve(
        self, query: str, top_k: int = 10, min_score: float = 0.1
    ) -> List[Dict]:
        """
        Hybrid retrieval: semantic + BM25 keyword matching.
        This is the default retrieval method.
        """
        query_embedding = embed_query(query)
        results = self.store.hybrid_search(
            query_embedding=query_embedding,
            query_text=query,
            top_k=top_k,
            min_score=min_score,
            semantic_weight=0.7,
            keyword_weight=0.3,
        )
        return results

    def retrieve_multi_query(
        self, query: str, sub_queries: Optional[List[str]] = None, top_k: int = 10
    ) -> List[Dict]:
        """
        Multi-query fusion retrieval.
        Expands a single query into multiple sub-queries, retrieves for each,
        then merges results using Reciprocal Rank Fusion (RRF).

        If sub_queries are not provided, generates them from the main query.
        """
        if sub_queries is None:
            sub_queries = self._expand_query(query)

        # Always include the original query
        all_queries = [query] + [q for q in sub_queries if q != query]

        # Retrieve for each query
        all_rankings: List[List[Dict]] = []
        for q in all_queries:
            q_embedding = embed_query(q)
            results = self.store.hybrid_search(
                query_embedding=q_embedding,
                query_text=q,
                top_k=top_k * 2,  # over-retrieve per query, trim after fusion
                min_score=0.05,
                semantic_weight=0.7,
                keyword_weight=0.3,
            )
            all_rankings.append(results)

        # Reciprocal Rank Fusion
        fused = self._reciprocal_rank_fusion(all_rankings, k=60)

        return fused[:top_k]

    def retrieve_filtered(
        self,
        query: str,
        source: Optional[str] = None,
        category: Optional[str] = None,
        section_contains: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict]:
        """
        Filtered hybrid retrieval — restrict search to specific metadata.

        Args:
            source: "public" or "private"
            category: Category name (for public data) or company name (for private)
            section_contains: Substring to match in section name
        """

        def filter_fn(meta: Dict) -> bool:
            if source and meta.get("source") != source:
                return False
            if category:
                cat = meta.get("category", meta.get("company", ""))
                if category.lower() not in cat.lower():
                    return False
            if section_contains:
                sec = meta.get("section", "")
                if section_contains.lower() not in sec.lower():
                    return False
            return True

        query_embedding = embed_query(query)
        return self.store.hybrid_search(
            query_embedding=query_embedding,
            query_text=query,
            top_k=top_k,
            filter_fn=filter_fn,
            semantic_weight=0.7,
            keyword_weight=0.3,
        )

    # ------------------------------------------------------------------
    # Full RAG (retrieve + generate)
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        top_k: int = 10,
        min_score: float = 0.1,
        use_multi_query: bool = True,
        return_context: bool = False,
    ) -> Dict:
        """
        Full RAG pipeline: retrieve relevant docs, then generate answer.

        Args:
            use_multi_query: If True, uses multi-query fusion for better recall.

        Returns:
            {
                "answer": str,
                "sources": [{"section", "source", "category", "score"}],
                "context_used": str  (only if return_context=True)
            }
        """
        # Step 1: Retrieve
        if use_multi_query:
            results = self.retrieve_multi_query(question, top_k=top_k)
        else:
            results = self.retrieve(question, top_k=top_k, min_score=min_score)

        if not results:
            return {
                "answer": "No relevant information found in the knowledge base for this query.",
                "sources": [],
            }

        # Step 2: Build context
        context_parts = []
        sources = []
        for i, r in enumerate(results):
            context_parts.append(
                f"--- Document {i+1} (relevance: {r['score']:.3f}) ---\n{r['text']}"
            )
            sources.append(
                {
                    "section": r["metadata"].get("section")
                    or r["metadata"].get("section_title", ""),
                    "source": r["metadata"].get("source", ""),
                    "category": r["metadata"].get(
                        "category", r["metadata"].get("company", "")
                    ),
                    "score": round(r["score"], 3),
                }
            )

        context = "\n\n".join(context_parts)

        # Step 3: Generate answer
        answer = self._generate(question, context)

        result = {"answer": answer, "sources": sources}
        if return_context:
            result["context_used"] = context

        return result

    def batch_retrieve(
        self, queries: List[str], top_k: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve for multiple queries at once.
        Uses multi-query fusion for each query.
        """
        all_results = {}
        for q in queries:
            all_results[q] = self.retrieve_multi_query(q, top_k=top_k)
        return all_results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _expand_query(query: str) -> List[str]:
        """
        Expand a query into multiple diverse sub-queries for fusion retrieval.
        This is a lightweight local expansion — no LLM call required.
        """
        sub_queries = []

        # Strategy 1: Rephrase with different focus keywords
        keywords = re.findall(r"[a-zA-Z]{3,}", query.lower())
        # Group keywords into pairs for focused sub-queries
        if len(keywords) >= 2:
            for i in range(0, min(len(keywords), 6), 2):
                pair = keywords[i : i + 2]
                sub_queries.append(" ".join(pair))

        # Strategy 2: Add investment-specific variations
        investment_prefixes = [
            "financial performance",
            "business operations",
            "key facts about",
        ]
        core = " ".join(keywords[:4]) if keywords else query
        for prefix in investment_prefixes:
            sub_queries.append(f"{prefix} {core}")

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for q in sub_queries:
            q_lower = q.strip().lower()
            if q_lower and q_lower not in seen:
                seen.add(q_lower)
                unique.append(q.strip())

        return unique[:5]  # cap at 5 sub-queries

    @staticmethod
    def _reciprocal_rank_fusion(rankings: List[List[Dict]], k: int = 60) -> List[Dict]:
        """
        Merge multiple ranked lists using Reciprocal Rank Fusion (RRF).
        RRF score = sum(1 / (k + rank_i)) across all rankings.
        """
        # Use document text as unique key
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict] = {}

        for ranking in rankings:
            for rank, result in enumerate(ranking):
                key = result["text"][:200]  # truncated text as key
                rrf_score = 1.0 / (k + rank + 1)
                doc_scores[key] = doc_scores.get(key, 0.0) + rrf_score
                # Keep the result with the highest individual score
                if key not in doc_map or result["score"] > doc_map[key]["score"]:
                    doc_map[key] = result

        # Sort by fused RRF score
        sorted_keys = sorted(
            doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True
        )

        results = []
        for key in sorted_keys:
            entry = doc_map[key].copy()
            entry["score"] = doc_scores[key]  # replace with RRF score
            results.append(entry)

        return results

    def _generate(self, question: str, context: str) -> str:
        """Generate an answer using Gemini with the retrieved context."""
        system_prompt = """You are an expert investment analyst assistant. 
You answer questions using ONLY the provided context from a company knowledge base.
Your answers should be:
- Factual and precise, citing specific data points where available
- Structured and clear, suitable for investment presentations
- Comprehensive but concise
- If financial data is available, include specific numbers and trends

If the context doesn't contain enough information to answer, say so explicitly.
Do NOT make up information not present in the context."""

        prompt = f"""CONTEXT FROM KNOWLEDGE BASE:
{context}

QUESTION: {question}

Provide a detailed, well-structured answer based on the context above."""

        for attempt in range(MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=GENERATION_MODEL,
                    contents=[system_prompt + "\n\n" + prompt],
                    config={"temperature": 0.2},
                )
                return response.text.strip()

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = 60
                    match = re.search(r"retryDelay': '(\d+)s", error_str)
                    if match:
                        wait_time = int(match.group(1))
                    print(f"Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                print(f"Generation error: {e}")
                raise

        return "Error: Could not generate answer after maximum retries."


# ======================================================================
# Presentation-specific retrieval
# ======================================================================

PRESENTATION_SECTIONS = {
    "company_overview": {
        "query": "Company overview history founding headquarters certifications mission",
        "sub_queries": [
            "company name founded year headquarters location",
            "business description domain segment",
            "certifications ISO quality standards",
        ],
    },
    "products_and_services": {
        "query": "Products services product portfolio manufacturing capabilities offerings",
        "sub_queries": [
            "product range forged machined components",
            "services engineering design prototyping logistics",
            "manufacturing hot cold warm forging machining",
        ],
    },
    "industries_served": {
        "query": "Industries served market segments automotive construction marine railway",
        "sub_queries": [
            "automotive passenger commercial vehicle",
            "industrial construction mining power generation",
            "marine railway agriculture applications",
        ],
    },
    "financial_performance": {
        "query": "Revenue profit EBITDA PAT financial results income statement balance sheet",
        "sub_queries": [
            "revenue from operations annual growth",
            "operating EBITDA profit after tax margin",
            "balance sheet borrowings net worth assets",
            "cash flow operating investing financing",
        ],
    },
    "strengths_and_competitive_edge": {
        "query": "Strengths competitive advantages market position experience technology",
        "sub_queries": [
            "strengths promoter experience market position",
            "technology capabilities advanced manufacturing",
            "competitive moat differentiation",
        ],
    },
    "weaknesses_and_risks": {
        "query": "Weaknesses risks threats challenges cyclicality working capital",
        "sub_queries": [
            "weaknesses working capital requirement",
            "risks raw material price volatility",
            "threats competition auto sector cyclicality",
        ],
    },
    "opportunities_and_growth": {
        "query": "Opportunities growth plans future strategy expansion capex",
        "sub_queries": [
            "growth revenue increase margin improvement",
            "future plan capex investment expansion",
            "export opportunities new markets",
        ],
    },
    "leadership_and_team": {
        "query": "Leadership management team board of directors key people executives",
        "sub_queries": [
            "managing director chairperson CFO",
            "board of directors independent directors",
            "employees departments operations engineering",
        ],
    },
    "shareholders_and_ownership": {
        "query": "Shareholders ownership promoters equity investor holdings",
        "sub_queries": [
            "promoter shareholding percentage",
            "institutional investors equity stake",
            "ownership structure public private",
        ],
    },
    "key_milestones": {
        "query": "Key milestones achievements timeline history important events",
        "sub_queries": [
            "founding milestones certification achievements",
            "order wins business development",
            "technology acquisition capacity expansion",
        ],
    },
    "certifications_and_quality": {
        "query": "Certifications ISO quality standards testing inspection",
        "sub_queries": [
            "ISO TS IATF OHSAS certifications",
            "testing metallurgical metrological laboratory",
            "quality control inspection processes",
        ],
    },
    "global_presence": {
        "query": "Global presence international operations exports geographic reach",
        "sub_queries": [
            "export markets India Europe United States Germany",
            "international subsidiaries offices",
            "global customers supply chain",
        ],
    },
    "clients_and_partnerships": {
        "query": "Clients customers partnerships key accounts business relationships",
        "sub_queries": [
            "major clients OEM customers",
            "top customers revenue contribution",
            "strategic partnerships collaborations",
        ],
    },
    "swot_analysis": {
        "query": "SWOT analysis strengths weaknesses opportunities threats",
        "sub_queries": [
            "strengths competitive advantages",
            "weaknesses risks challenges",
            "opportunities growth potential market expansion",
            "threats competition raw material volatility",
        ],
    },
    "credit_and_ratings": {
        "query": "Credit rating credit status CRISIL financial health",
        "sub_queries": [
            "CRISIL rating BBB credit assessment",
            "credit instruments term loan cash credit",
            "financial risk profile gearing coverage",
        ],
    },
    "market_landscape": {
        "query": "Market size industry trends competitive landscape peers",
        "sub_queries": [
            "market size automotive forging industry",
            "peer companies competitors",
            "industry growth trends outlook",
        ],
    },
}


def retrieve_for_presentation(
    engine: RAGEngine, top_k: int = 8
) -> Dict[str, List[Dict]]:
    """
    Pre-retrieve data for all standard investment presentation sections.
    Uses multi-query fusion for comprehensive context per section.
    Returns a dict mapping section names to retrieved documents.
    """
    print("Retrieving data for presentation sections...")
    section_data = {}

    for section_key, config in PRESENTATION_SECTIONS.items():
        print(f"  [{section_key}] querying with multi-query fusion...")
        results = engine.retrieve_multi_query(
            query=config["query"],
            sub_queries=config["sub_queries"],
            top_k=top_k,
        )
        section_data[section_key] = results
        print(f"    -> {len(results)} documents retrieved")

    return section_data
