"""
Agent 1 — Company Understanding Agent

First reasoning layer. Retrieves broad company data from the RAG engine
and produces a structured company profile used by all downstream agents.
"""

import json
import sys
import os
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root and RAG dir are on sys.path for RAG's internal imports
_project_root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "RAG"))

# Load env before RAG (which eagerly creates Gemini client)
for _env in [
    os.path.join(_project_root, "RAG", ".env"),
    os.path.join(_project_root, "Agents", ".env"),
]:
    if os.path.exists(_env):
        load_dotenv(_env)

from RAG.rag_engine import RAGEngine
from Agents.state import PresentationState
from Agents.llm import call_llm


PROMPT_PATH = Path(__file__).parent / "prompts" / "company_understanding.md"

# Broad queries to retrieve comprehensive company data
PROFILE_QUERIES = [
    {
        "query": "Company overview business description products services industry",
        "sub_queries": [
            "company name founded year headquarters",
            "business description core operations",
            "products services offerings portfolio",
        ],
    },
    {
        "query": "Revenue profit financial performance metrics growth",
        "sub_queries": [
            "revenue from operations annual",
            "profit after tax EBITDA margin",
            "growth rate CAGR trend",
        ],
    },
    {
        "query": "Market position competitive strengths target customers",
        "sub_queries": [
            "major clients customers OEM",
            "market position competitive advantage",
            "export domestic geographic presence",
        ],
    },
    {
        "query": "Employees management shareholders ownership structure",
        "sub_queries": [
            "promoter shareholding ownership",
            "employees departments team size",
            "company stage maturity listing status",
        ],
    },
]


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def _retrieve_company_context(engine: RAGEngine, company_name: str) -> str:
    """Retrieve broad context about the company from all data sources."""
    all_chunks = []
    for qconfig in PROFILE_QUERIES:
        # Inject company name into queries for targeted retrieval
        main_q = f"{company_name} {qconfig['query']}"
        sub_qs = [f"{company_name} {sq}" for sq in qconfig["sub_queries"]]
        results = engine.retrieve_multi_query(query=main_q, sub_queries=sub_qs, top_k=6)
        all_chunks.extend(results)

    # Deduplicate by text content
    seen = set()
    unique_chunks = []
    for chunk in all_chunks:
        key = chunk["text"][:200]
        if key not in seen:
            seen.add(key)
            unique_chunks.append(chunk)

    # Build context string
    context_parts = []
    for i, chunk in enumerate(unique_chunks):
        source = chunk["metadata"].get("source", "unknown")
        section = chunk["metadata"].get(
            "section", chunk["metadata"].get("section_title", "")
        )
        context_parts.append(
            f"--- Document {i+1} [source: {source}, section: {section}] ---\n{chunk['text']}"
        )

    return "\n\n".join(context_parts)


def _parse_profile(raw_response: str) -> dict:
    """Extract JSON from the LLM response."""
    # Try to find JSON block in the response
    text = raw_response.strip()
    # Remove markdown code fences if present
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]

    return json.loads(text.strip())


def run(state: PresentationState) -> dict:
    """
    LangGraph node function.
    Retrieves company data and produces a structured company profile.
    """
    company_name = state["company_name"]
    print(f"\n{'='*60}")
    print(f"[Agent 1] Company Understanding — {company_name}")
    print(f"{'='*60}")

    # Initialize RAG engine
    engine = RAGEngine(index_path=os.path.join("RAG", "index"))

    # Retrieve broad context
    print("  Retrieving company data from knowledge base...")
    context = _retrieve_company_context(engine, company_name)
    print(f"  Retrieved context: {len(context)} characters")

    # Build LLM prompt
    system_prompt = _load_prompt()
    user_prompt = f"""COMPANY NAME: {company_name}

RETRIEVED CONTEXT:
{context}

Analyze the above context and produce the structured company profile JSON. Remember — every field must be grounded in the evidence."""

    # Call LLM
    print("  Generating company profile...")
    raw_response = call_llm(system_prompt, user_prompt)
    profile = _parse_profile(raw_response)
    print(
        f"  Profile generated: {profile.get('company_category', '?')} / {profile.get('industry', '?')}"
    )
    print(
        f"  Stage: {profile.get('stage', '?')} | Audience: {profile.get('investor_audience', '?')}"
    )

    return {"company_profile": profile}
