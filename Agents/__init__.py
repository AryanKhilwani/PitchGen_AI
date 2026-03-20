"""
Agents — Agentic Investment Presentation Generator

A multi-agent LangGraph pipeline that generates polished .pptx
investment presentations from indexed company data.

Usage:
    python -m Agents.orchestrator "Kalyani Forge"

Pipeline:
    1. Company Understanding → structured profile
    2. Presentation Strategy → slide plan + story arc
    3. Data Grounding → evidence-checked plan + chartable data
    4. Slide Content → text content per slide
    5. Quality Assurance → consistency/accuracy review (loops if needed)
    6. Slide Design → layout + composition + deck theme
    7. Visual QA → design variety check (loops if needed)
    8. Image Generation → AI hero visuals for selected slides
    9. PPTX Renderer → .pptx file (deterministic)
"""
