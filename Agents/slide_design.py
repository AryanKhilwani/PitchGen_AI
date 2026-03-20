"""
Agent 6 — Slide Design Agent

Assigns visual layout, component composition, chart types, color schemes,
text hierarchy, and deck theme to each slide. Reads visual_intent from
Agent 4 to produce component-based compositions. Outputs machine-readable
design specs for the renderer.
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
    Takes QA-approved slide contents + company profile, outputs design specs
    and a deck-level theme.
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
    visual_structures_map = {}
    for entry in grounded_plan:
        sid = entry.get("slide_id", "")
        chartable = entry.get("chartable_data", [])
        if chartable:
            chartable_map[sid] = chartable
        vis_structs = entry.get("visual_structures", {})
        if vis_structs:
            visual_structures_map[sid] = vis_structs

    system_prompt = _load_prompt()
    user_prompt = f"""COMPANY PROFILE:
Industry: {company_profile.get('industry', 'unknown')}
Category: {company_profile.get('company_category', 'unknown')}
Stage: {company_profile.get('stage', 'unknown')}

SLIDE CONTENTS ({len(slide_contents)} slides):
{json.dumps(slide_contents, indent=2)}

CHARTABLE DATA AVAILABLE:
{json.dumps(chartable_map, indent=2)}

VISUAL STRUCTURES FROM GROUNDING:
{json.dumps(visual_structures_map, indent=2)}

For each slide, assign layout, component composition, chart type, colors, and text hierarchy.
Also output a single deck_theme object for the whole presentation.
Output strict JSON object with "deck_theme" and "slides" keys as specified in your instructions."""

    print(f"  Designing {len(slide_contents)} slides...")
    print(f"  Chartable data available for {len(chartable_map)} slides")
    print(f"  Visual structures available for {len(visual_structures_map)} slides")
    raw_response = call_llm(system_prompt, user_prompt)

    # Parse response
    text = raw_response.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]

    parsed = json.loads(text.strip())

    # Handle both new format {deck_theme, slides} and legacy format (plain array)
    if isinstance(parsed, dict):
        deck_theme = parsed.get("deck_theme", {})
        design_specs = parsed.get("slides", [])
    else:
        # Legacy: plain array of slide specs
        deck_theme = {}
        design_specs = parsed

    # Ensure every slide spec has slide_mood and background_treatment defaults
    _VALID_MOODS = {"bold", "light", "editorial", "data", "accent"}
    _VALID_BG = {
        "solid_surface",
        "gradient_brand",
        "full_bleed_image",
        "split_image",
        "dark_solid",
        "subtle_pattern",
    }
    for spec in design_specs:
        mood = spec.get("slide_mood", "")
        if mood not in _VALID_MOODS:
            spec["slide_mood"] = "light"
        bg = spec.get("background_treatment", "")
        if bg not in _VALID_BG:
            spec["background_treatment"] = "solid_surface"

    print(f"  Design specs generated for {len(design_specs)} slides:")
    for spec in design_specs:
        layout = spec.get("layout", "?")
        chart = spec.get("chart_type", "none")
        comp_count = len((spec.get("composition") or {}).get("components", []))
        comp_info = f", {comp_count} components" if comp_count else ""
        mood_info = f", mood={spec.get('slide_mood', 'light')}"
        print(
            f"    - [{spec.get('slide_id')}] layout={layout}, chart={chart}{comp_info}{mood_info}"
        )

    if deck_theme:
        font_pair = deck_theme.get("font_pair", {})
        print(
            f"  Deck theme: {font_pair.get('heading', '?')}/{font_pair.get('body', '?')}, "
            f"style={deck_theme.get('illustration_style', '?')}"
        )

    result = {"design_specs": design_specs}
    if deck_theme:
        result["deck_theme"] = deck_theme
    return result
