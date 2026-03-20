"""
Agent 3 — Data Grounding Agent

Reality-checks the ideal slide plan against actual evidence in the knowledge base.
Scores evidence availability, extracts chartable numeric data,
and decides which slides to keep, merge, drop, or add.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_project_root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "RAG"))

for _env in [
    os.path.join(_project_root, "RAG", ".env"),
    os.path.join(_project_root, "Agents", ".env"),
]:
    if os.path.exists(_env):
        load_dotenv(_env)

from RAG.rag_engine import RAGEngine
from Agents.state import PresentationState
from Agents.llm import call_llm


PROMPT_PATH = Path(__file__).parent / "prompts" / "data_grounding.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def _retrieve_evidence_for_slide(
    engine: RAGEngine, company_name: str, slide: dict
) -> list[dict]:
    """Retrieve evidence chunks relevant to a specific slide."""
    title = slide.get("title", "")
    purpose = slide.get("purpose", "")
    key_questions = slide.get("key_questions", [])

    # Build targeted queries from the slide specification
    main_query = f"{company_name} {title} {purpose}"
    sub_queries = [f"{company_name} {q}" for q in key_questions[:3]]

    if not sub_queries:
        sub_queries = [f"{company_name} {title}"]

    results = engine.retrieve_multi_query(
        query=main_query, sub_queries=sub_queries, top_k=8
    )

    return [
        {
            "text": r["text"],
            "score": round(r["score"], 4),
            "metadata": r["metadata"],
        }
        for r in results
    ]


def run(state: PresentationState) -> dict:
    """
    LangGraph node function.
    Retrieves evidence for each planned slide and produces a grounded plan.
    """
    company_name = state["company_name"]
    slide_plan = state["slide_plan"]

    print(f"\n{'='*60}")
    print(f"[Agent 3] Data Grounding — {company_name}")
    print(f"{'='*60}")

    engine = RAGEngine(index_path=os.path.join("RAG", "index"))

    # Retrieve evidence for each slide
    slides_with_evidence = []
    for slide in slide_plan:
        slide_id = slide.get("slide_id", "unknown")
        print(f"  Retrieving evidence for [{slide_id}]...")
        evidence = _retrieve_evidence_for_slide(engine, company_name, slide)
        print(
            f"    -> {len(evidence)} chunks (top score: {evidence[0]['score']:.3f})"
            if evidence
            else "    -> 0 chunks"
        )
        slides_with_evidence.append(
            {
                "slide": slide,
                "evidence": evidence,
            }
        )

    # Build the LLM prompt with all slides + evidence
    system_prompt = _load_prompt()

    slides_context = []
    for item in slides_with_evidence:
        slide = item["slide"]
        evidence = item["evidence"]
        evidence_text = "\n".join(
            f"  [{i+1}] (score: {e['score']}) "
            f"[hints: {','.join(e.get('metadata', {}).get('content_hints', ['general']))}] "
            f"{e['text'][:500]}"
            for i, e in enumerate(evidence[:6])
        )
        slides_context.append(
            f"""SLIDE: {slide.get('slide_id')}
Title: {slide.get('title')}
Purpose: {slide.get('purpose')}
Key Questions: {json.dumps(slide.get('key_questions', []))}
EVIDENCE ({len(evidence)} chunks):
{evidence_text}
"""
        )

    user_prompt = f"""COMPANY: {company_name}

PLANNED SLIDES WITH RETRIEVED EVIDENCE:

{"---".join(slides_context)}

For each slide, evaluate the evidence quality, extract any chartable numeric data AND visual structures (timelines, process steps, cycles, comparisons, hierarchies, card items), and decide the action (keep/merge/drop/add).
Output strict JSON array as specified in your instructions."""

    print("  Evaluating evidence and grounding the plan...")
    raw_response = call_llm(system_prompt, user_prompt)

    # Parse response
    text = raw_response.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]
    grounded_plan = json.loads(text.strip())

    # Attach the raw evidence chunks to each grounded slide for Agent 4
    evidence_map = {
        item["slide"]["slide_id"]: item["evidence"] for item in slides_with_evidence
    }
    for entry in grounded_plan:
        sid = entry.get("slide_id", "")
        if sid in evidence_map:
            entry["evidence_chunks"] = evidence_map[sid]
        elif "evidence_chunks" not in entry:
            entry["evidence_chunks"] = []

    # Report
    kept = sum(1 for e in grounded_plan if e.get("action") == "keep")
    merged = sum(
        1 for e in grounded_plan if str(e.get("action", "")).startswith("merge")
    )
    dropped = sum(1 for e in grounded_plan if e.get("action") == "drop")
    added = sum(1 for e in grounded_plan if e.get("action") == "add")
    vis_count = sum(
        1
        for e in grounded_plan
        if e.get("visual_structures", {}).get("semantic_trigger")
        and e["visual_structures"]["semantic_trigger"]
        not in ("narrative_prose", "grouped_metrics")
    )
    print(f"  Grounded plan: {kept} keep, {merged} merge, {dropped} drop, {added} add")
    print(f"  Visual structures extracted for {vis_count} slides")

    return {"grounded_plan": grounded_plan}
