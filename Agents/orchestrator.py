"""
Orchestrator — LangGraph StateGraph definition and runner.

Defines the 6-agent pipeline with a QA feedback loop:
    company_understanding → presentation_strategy → data_grounding
    → slide_content → quality_assurance → (conditional loop or proceed)
    → slide_design → pptx_render
"""

import os
import sys
import json
import time

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langgraph.graph import StateGraph, END

from Agents.state import PresentationState
from Agents import (
    company_understanding,
    presentation_strategy,
    data_grounding,
    slide_content,
    quality_assurance,
    slide_design,
)
from Agents.pptx_renderer import render as pptx_render
from Agents.image_generator import generate_images_for_slides


# Maximum QA revision loops before forcing approval
MAX_QA_REVISIONS = 4


def _qa_router(state: PresentationState) -> str:
    """
    Conditional edge after QA: loop back to slide_content if critical
    issues found and we haven't exceeded max revisions.
    """
    qa_report = state.get("qa_report", {})
    revision_count = state.get("qa_revision_count", 0)

    approved = qa_report.get("approved", False)
    has_critical = any(
        i.get("severity") == "critical" for i in qa_report.get("issues", [])
    )

    if approved or revision_count >= MAX_QA_REVISIONS:
        if not approved:
            print(
                f"\n  [QA] Max revisions ({MAX_QA_REVISIONS}) reached. Proceeding despite issues."
            )
        return "slide_design"
    elif has_critical:
        print(
            f"\n  [QA] Critical issues found. Routing back to slide_content (revision {revision_count + 1})..."
        )
        return "slide_content"
    else:
        return "slide_design"


def build_graph() -> StateGraph:
    """Build and compile the LangGraph presentation pipeline."""
    graph = StateGraph(PresentationState)

    # Add nodes
    graph.add_node("company_understanding", company_understanding.run)
    graph.add_node("presentation_strategy", presentation_strategy.run)
    graph.add_node("data_grounding", data_grounding.run)
    graph.add_node("slide_content", slide_content.run)
    graph.add_node("quality_assurance", quality_assurance.run)
    graph.add_node("slide_design", slide_design.run)
    graph.add_node("image_generation", generate_images_for_slides)
    graph.add_node("pptx_render", pptx_render)

    # Define edges (sequential pipeline with one conditional)
    graph.set_entry_point("company_understanding")
    graph.add_edge("company_understanding", "presentation_strategy")
    graph.add_edge("presentation_strategy", "data_grounding")
    graph.add_edge("data_grounding", "slide_content")
    graph.add_edge("slide_content", "quality_assurance")

    # Conditional edge: QA either approves → design, or loops → content
    graph.add_conditional_edges(
        "quality_assurance",
        _qa_router,
        {
            "slide_design": "slide_design",
            "slide_content": "slide_content",
        },
    )

    graph.add_edge("slide_design", "image_generation")
    graph.add_edge("image_generation", "pptx_render")
    graph.add_edge("pptx_render", END)

    return graph.compile()


def generate_presentation(company_name: str) -> str:
    """
    Main entry point. Generates an investment presentation for the given company.
    Returns the path to the generated .pptx file.
    """
    print(f"\n{'#'*60}")
    print(f"# Generating Investment Presentation")
    print(f"# Company: {company_name}")
    print(f"{'#'*60}")

    start_time = time.time()

    # Build the pipeline
    app = build_graph()

    # Initial state
    initial_state: PresentationState = {
        "company_name": company_name,
        "company_profile": {},
        "slide_plan": [],
        "grounded_plan": [],
        "slide_contents": [],
        "qa_report": {"approved": False, "issues": [], "summary": ""},
        "qa_revision_count": 0,
        "qa_feedback": "",
        "design_specs": [],
        "image_map": {},
        "pptx_path": "",
    }

    # Run the pipeline
    final_state = app.invoke(initial_state)

    elapsed = time.time() - start_time
    pptx_path = final_state.get("pptx_path", "")

    print(f"\n{'#'*60}")
    print(f"# DONE — {elapsed:.1f}s")
    print(f"# Output: {pptx_path}")
    print(f"# Slides: {len(final_state.get('slide_contents', []))}")
    print(f"# QA Passes: {final_state.get('qa_revision_count', 0)}")
    print(f"# QA Approved: {final_state.get('qa_report', {}).get('approved', '?')}")
    print(f"{'#'*60}")

    # Save intermediate state for debugging
    debug_dir = os.path.join("Agents", "outputs")
    os.makedirs(debug_dir, exist_ok=True)
    safe_name = company_name.replace(" ", "_").replace("/", "-")
    debug_path = os.path.join(debug_dir, f"{safe_name}_debug_state.json")

    debug_data = {
        "company_name": final_state.get("company_name"),
        "company_profile": final_state.get("company_profile"),
        "slide_plan": final_state.get("slide_plan"),
        "grounded_plan_count": len(final_state.get("grounded_plan", [])),
        "slide_contents": final_state.get("slide_contents"),
        "qa_report": final_state.get("qa_report"),
        "qa_revision_count": final_state.get("qa_revision_count"),
        "design_specs": final_state.get("design_specs"),
        "pptx_path": final_state.get("pptx_path"),
    }

    with open(debug_path, "w") as f:
        json.dump(debug_data, f, indent=2, default=str)
    print(f"  Debug state saved: {debug_path}")

    return pptx_path


# CLI entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m Agents.orchestrator <company_name>")
        print("Example: python -m Agents.orchestrator 'Kalyani Forge'")
        sys.exit(1)

    company = sys.argv[1]
    result = generate_presentation(company)
    print(f"\nPresentation saved to: {result}")
