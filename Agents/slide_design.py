"""
Agent 6 — Slide Design Agent

Assigns visual layout, chart types, color schemes, and text hierarchy
to each slide. Outputs machine-readable design specs for the renderer.
"""

import json
from pathlib import Path

from Agents.state import PresentationState
from Agents.llm import call_llm


PROMPT_PATH = Path(__file__).parent / "prompts" / "slide_design.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def run(state: PresentationState) -> dict:
    """
    LangGraph node function.
    Takes QA-approved slide contents + company profile, outputs design specs.
    """
    company_name = state["company_name"]
    slide_contents = state["slide_contents"]
    company_profile = state["company_profile"]
    grounded_plan = state["grounded_plan"]

    print(f"\n{'='*60}")
    print(f"[Agent 6] Slide Design — {company_name}")
    print(f"{'='*60}")

    # Build a chartable data map from the grounded plan
    chartable_map = {}
    for entry in grounded_plan:
        sid = entry.get("slide_id", "")
        chartable = entry.get("chartable_data", [])
        if chartable:
            chartable_map[sid] = chartable

    system_prompt = _load_prompt()
    user_prompt = f"""COMPANY PROFILE:
Industry: {company_profile.get('industry', 'unknown')}
Category: {company_profile.get('company_category', 'unknown')}
Stage: {company_profile.get('stage', 'unknown')}

SLIDE CONTENTS ({len(slide_contents)} slides):
{json.dumps(slide_contents, indent=2)}

CHARTABLE DATA AVAILABLE:
{json.dumps(chartable_map, indent=2)}

For each slide, assign layout, chart type, colors, and text hierarchy.
Output strict JSON array as specified in your instructions."""

    print(f"  Designing {len(slide_contents)} slides...")
    print(f"  Chartable data available for {len(chartable_map)} slides")
    raw_response = call_llm(system_prompt, user_prompt)

    # Parse response
    text = raw_response.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]
    design_specs = json.loads(text.strip())

    print(f"  Design specs generated for {len(design_specs)} slides:")
    for spec in design_specs:
        layout = spec.get("layout", "?")
        chart = spec.get("chart_type", "none")
        print(f"    - [{spec.get('slide_id')}] layout={layout}, chart={chart}")

    return {"design_specs": design_specs}
