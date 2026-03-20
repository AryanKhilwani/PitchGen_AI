"""
Agent 5 — Quality Assurance Agent

Reviews all slide contents for consistency, accuracy, narrative coherence,
and investment-grade quality. Can trigger a re-run of the Slide Content Agent
via LangGraph conditional edge if critical issues are found.
"""

import json
from pathlib import Path

from Agents.state import PresentationState
from Agents.llm import call_llm


PROMPT_PATH = Path(__file__).parent / "prompts" / "quality_assurance.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def _check_visual_variety(slide_contents: list) -> list:
    """Programmatic check for layout repetition and visual monotony."""
    issues = []
    visual_types = []
    text_heavy = []

    for sc in slide_contents:
        vi = sc.get("visual_intent", {})
        vt = vi.get("visual_type", sc.get("layout", "unknown"))
        visual_types.append(vt)
        bullets = sc.get("bullets", [])
        if len(bullets) >= 6 and not vi.get("visual_type"):
            text_heavy.append(sc.get("slide_id", "?"))

    # Check for 3+ consecutive identical visual types
    for i in range(len(visual_types) - 2):
        if visual_types[i] == visual_types[i + 1] == visual_types[i + 2]:
            issues.append(
                {
                    "slide_id": slide_contents[i + 2].get("slide_id", "?"),
                    "severity": "warning",
                    "description": (
                        f"3 consecutive slides use the same visual type "
                        f"'{visual_types[i]}' (slides {i + 1}-{i + 3}). "
                        f"This feels monotonous."
                    ),
                    "fix_suggestion": (
                        "Convert one of these slides to a different visual: "
                        "timeline, card_grid, kpi_strip, or process_flow."
                    ),
                }
            )
            break  # one warning is enough

    # Flag text-heavy slides
    for sid in text_heavy[:2]:
        issues.append(
            {
                "slide_id": sid,
                "severity": "info",
                "description": f"Slide '{sid}' has 6+ bullets with no visual component.",
                "fix_suggestion": (
                    "Consider converting to a card_grid, comparison_matrix, "
                    "or icon_fact_grid for better visual engagement."
                ),
            }
        )

    # Check overall diversity
    unique = set(visual_types)
    if len(visual_types) >= 5 and len(unique) <= 2:
        issues.append(
            {
                "slide_id": "deck_overall",
                "severity": "warning",
                "description": (
                    f"Only {len(unique)} distinct visual types used across "
                    f"{len(visual_types)} slides. Deck feels templated."
                ),
                "fix_suggestion": "Vary layouts — add kpi_strip, timeline, or process_flow slides.",
            }
        )

    return issues


def run(state: PresentationState) -> dict:
    """
    LangGraph node function.
    Reviews all slides and outputs a QA report.
    """
    company_name = state["company_name"]
    slide_contents = state["slide_contents"]
    company_profile = state["company_profile"]
    revision_count = state.get("qa_revision_count", 0)

    print(f"\n{'='*60}")
    print(f"[Agent 5] Quality Assurance — {company_name} (pass {revision_count + 1})")
    print(f"{'='*60}")

    system_prompt = _load_prompt()
    user_prompt = f"""COMPANY PROFILE:
{json.dumps(company_profile, indent=2)}

COMPLETE SLIDE CONTENTS ({len(slide_contents)} slides):
{json.dumps(slide_contents, indent=2)}

Review all slides across all review dimensions. Output strict JSON as specified in your instructions."""

    print("  Reviewing slides for quality and consistency...")
    raw_response = call_llm(system_prompt, user_prompt)

    # Parse response
    text = raw_response.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]
    qa_report = json.loads(text.strip())

    # Merge programmatic visual variety issues
    variety_issues = _check_visual_variety(slide_contents)
    qa_report.setdefault("issues", []).extend(variety_issues)

    # Count issues by severity
    issues = qa_report.get("issues", [])
    critical = sum(1 for i in issues if i.get("severity") == "critical")
    warnings = sum(1 for i in issues if i.get("severity") == "warning")
    info = sum(1 for i in issues if i.get("severity") == "info")

    approved = qa_report.get("approved", False)
    print(f"  Issues found: {critical} critical, {warnings} warning, {info} info")
    print(f"  Approved: {approved}")
    print(f"  Summary: {qa_report.get('summary', 'N/A')}")

    # Build QA feedback string for potential Slide Content re-run
    qa_feedback = ""
    if not approved and critical > 0:
        feedback_parts = []
        for issue in issues:
            if issue.get("severity") in ("critical", "warning"):
                feedback_parts.append(
                    f"[{issue.get('severity').upper()}] Slide '{issue.get('slide_id')}': "
                    f"{issue.get('description')} → Fix: {issue.get('fix_suggestion')}"
                )
        qa_feedback = "\n".join(feedback_parts)

    return {
        "qa_report": qa_report,
        "qa_revision_count": revision_count + 1,
        "qa_feedback": qa_feedback,
    }
