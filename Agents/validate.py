"""Quick validation: imports, graph compilation, module completeness."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def main():
    print("Testing imports...")

    # Load .env files before importing RAG (which eagerly creates a Gemini client)
    from dotenv import load_dotenv

    env_locations = [
        os.path.join(os.path.dirname(__file__), "..", "RAG", ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(__file__), "..", ".env"),
    ]
    for env_path in env_locations:
        if os.path.exists(env_path):
            load_dotenv(env_path)

    from Agents.state import PresentationState

    print("  state.py OK")

    from Agents.llm import call_llm

    print("  llm.py OK")

    from Agents import company_understanding

    print("  company_understanding.py OK")

    from Agents import presentation_strategy

    print("  presentation_strategy.py OK")

    from Agents import data_grounding

    print("  data_grounding.py OK")

    from Agents import slide_content

    print("  slide_content.py OK")

    from Agents import quality_assurance

    print("  quality_assurance.py OK")

    from Agents import slide_design

    print("  slide_design.py OK")

    from Agents.pptx_renderer import render

    print("  pptx_renderer.py OK")

    from Agents.orchestrator import build_graph, generate_presentation

    print("  orchestrator.py OK")

    # Verify all agents have run() function
    for mod_name, mod in [
        ("company_understanding", company_understanding),
        ("presentation_strategy", presentation_strategy),
        ("data_grounding", data_grounding),
        ("slide_content", slide_content),
        ("quality_assurance", quality_assurance),
        ("slide_design", slide_design),
    ]:
        assert hasattr(mod, "run"), f"{mod_name} missing run()"
        assert callable(mod.run), f"{mod_name}.run is not callable"

    print("\nAll agent modules have run() functions OK")

    # Test graph compilation
    print("\nCompiling LangGraph pipeline...")
    app = build_graph()
    nodes = list(app.get_graph().nodes.keys())
    print(f"  Graph compiled OK")
    print(f"  Nodes: {nodes}")

    # Verify prompt files exist
    from pathlib import Path

    prompts_dir = Path(__file__).parent / "prompts"
    expected = [
        "company_understanding.md",
        "presentation_strategy.md",
        "data_grounding.md",
        "slide_content.md",
        "quality_assurance.md",
        "slide_design.md",
    ]
    for fn in expected:
        p = prompts_dir / fn
        assert p.exists(), f"Missing prompt: {p}"
        size = p.stat().st_size
        print(f"  prompt {fn}: {size} bytes")

    print("\nAll validations passed!")


if __name__ == "__main__":
    main()
