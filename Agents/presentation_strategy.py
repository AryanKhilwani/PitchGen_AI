"""
Agent 2 — Presentation Strategy Agent

Decides the investment story arc, slide sequence, and evaluation factors
based on the structured company profile from Agent 1.
No RAG retrieval needed — pure reasoning over the company profile.
"""

import json
from pathlib import Path

from Agents.state import PresentationState
from Agents.llm import call_llm


PROMPT_PATH = Path(__file__).parent / "prompts" / "presentation_strategy.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def _parse_strategy(raw_response: str) -> dict:
    """Extract JSON from the LLM response."""
    text = raw_response.strip()
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
    Takes company profile, outputs slide plan with story arc.
    """
    profile = state["company_profile"]
    print(f"\n{'='*60}")
    print(
        f"[Agent 2] Presentation Strategy — {profile.get('company_name', state['company_name'])}"
    )
    print(f"{'='*60}")

    system_prompt = _load_prompt()
    user_prompt = f"""COMPANY PROFILE:
{json.dumps(profile, indent=2)}

Based on this company profile, design the optimal presentation strategy and slide sequence.
Output strict JSON as specified in your instructions."""

    print("  Designing presentation strategy...")
    raw_response = call_llm(system_prompt, user_prompt)
    strategy = _parse_strategy(raw_response)

    slide_plan = strategy.get("slide_sequence", [])
    print(f"  Story arc: {strategy.get('story_arc', '?')}")
    print(f"  Planned slides: {len(slide_plan)}")
    for s in slide_plan:
        print(f"    - [{s.get('slide_id')}] {s.get('title')}")

    # Store the full strategy in slide_plan entries as metadata
    for slide in slide_plan:
        slide["evaluation_factors"] = strategy.get("evaluation_factors", [])

    return {
        "slide_plan": slide_plan,
    }
