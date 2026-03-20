"""
Agent 4 — Slide Content Agent

Generates polished, evidence-backed text content for every slide
in the grounded plan. Each slide gets title, bullets, key takeaway,
supporting data, references, and speaker notes.
"""

import json
from pathlib import Path

from Agents.state import PresentationState
from Agents.llm import call_llm


PROMPT_PATH = Path(__file__).parent / "prompts" / "slide_content.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def _build_slide_context(grounded_plan: list[dict]) -> str:
    """Format the grounded plan with evidence for the LLM."""
    parts = []
    for entry in grounded_plan:
        action = entry.get("action", "keep")
        if action == "drop":
            continue  # Skip dropped slides

        slide_id = entry.get("slide_id", "unknown")
        title = entry.get("title", "")
        purpose = entry.get("purpose", "")
        confidence = entry.get("confidence", "unknown")
        data_gaps = entry.get("data_gaps", [])
        chartable = entry.get("chartable_data", [])
        visual_structs = entry.get("visual_structures", {})
        evidence = entry.get("evidence_chunks", [])

        # Format evidence
        evidence_text = ""
        if evidence:
            evidence_items = []
            for i, e in enumerate(evidence[:6]):
                text = e.get("text", "") if isinstance(e, dict) else str(e)
                evidence_items.append(f"  [{i+1}] {text[:600]}")
            evidence_text = "\n".join(evidence_items)

        chartable_text = json.dumps(chartable, indent=2) if chartable else "None"
        visual_structs_text = (
            json.dumps(visual_structs, indent=2) if visual_structs else "None"
        )

        parts.append(
            f"""SLIDE: {slide_id}
Title: {title}
Purpose: {purpose}
Confidence: {confidence}
Action: {action}
Data Gaps: {json.dumps(data_gaps)}
Chartable Data: {chartable_text}
Visual Structures: {visual_structs_text}
Evidence:
{evidence_text}
"""
        )

    return "\n---\n".join(parts)


def run(state: PresentationState) -> dict:
    """
    LangGraph node function.
    Generates slide content for all non-dropped slides in the grounded plan.
    """
    company_name = state["company_name"]
    grounded_plan = state["grounded_plan"]
    qa_feedback = state.get("qa_feedback", "")

    print(f"\n{'='*60}")
    print(f"[Agent 4] Slide Content — {company_name}")
    print(f"{'='*60}")

    # Count active slides
    active_slides = [s for s in grounded_plan if s.get("action") != "drop"]
    print(f"  Generating content for {len(active_slides)} slides...")

    system_prompt = _load_prompt()
    slides_context = _build_slide_context(grounded_plan)

    user_prompt = f"""COMPANY: {company_name}

GROUNDED SLIDE PLAN WITH EVIDENCE:

{slides_context}"""

    # Add QA feedback if this is a revision pass
    if qa_feedback:
        user_prompt += f"""

QA FEEDBACK FROM PREVIOUS PASS (address these issues):
{qa_feedback}
"""
        print("  (Revision pass — addressing QA feedback)")

    user_prompt += """

Generate complete slide content for each active slide. Include a visual_intent object for every slide.
Output strict JSON array as specified in your instructions.
Every claim must be grounded in the provided evidence — do NOT fabricate data."""

    raw_response = call_llm(system_prompt, user_prompt)

    # Parse response
    text = raw_response.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]
    slide_contents = json.loads(text.strip())

    print(f"  Generated {len(slide_contents)} slides:")
    for s in slide_contents:
        n_bullets = len(s.get("bullets", []))
        vis_type = (s.get("visual_intent") or {}).get("visual_type", "none")
        print(
            f"    - [{s.get('slide_id')}] {s.get('title')} ({n_bullets} bullets, visual={vis_type})"
        )

    return {"slide_contents": slide_contents}
