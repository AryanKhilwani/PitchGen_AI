"""
Shared state schema for the presentation generation pipeline.

This TypedDict flows through all LangGraph nodes.
Each agent reads what it needs and writes its output fields.
"""

from typing import TypedDict, Optional


class ChartableData(TypedDict):
    label: str  # e.g. "Revenue (₹ Cr)"
    data_points: list[dict]  # [{year: "FY13", value: 1200}, ...]
    chart_hint: str  # "line" | "bar" | "pie"


class EvidenceChunk(TypedDict):
    text: str
    score: float
    metadata: dict


class SlideEvidence(TypedDict):
    slide_id: str
    title: str
    purpose: str
    confidence: str  # "high" | "medium" | "low"
    evidence_chunks: list[EvidenceChunk]
    chartable_data: list[ChartableData]
    data_gaps: list[str]
    action: str  # "keep" | "merge_with:<id>" | "drop" | "add"
    notes: str


class SlideContent(TypedDict):
    slide_id: str
    title: str
    subtitle: Optional[str]
    content_type: (
        str  # "bullets" | "metrics" | "comparison" | "timeline" | "text_block"
    )
    bullets: list[str]
    key_takeaway: str
    supporting_data: list[str]
    data_references: list[str]
    speaker_notes: str
    suggested_visual: Optional[
        str
    ]  # "bar_chart" | "pie_chart" | "timeline" | "table" | "icon_grid" | "image_placeholder"


class SlideDesignSpec(TypedDict):
    slide_id: str
    layout: str  # "title_slide" | "title_content" | "two_column" | "section_header" | "chart_slide" | "blank"
    chart_type: Optional[str]  # "bar" | "line" | "pie" | "table" | None
    chart_data: Optional[dict]
    color_accent: str  # Hex color
    icon_suggestions: list[str]
    text_hierarchy: dict  # {element: {size, bold, font, color}} per element
    visual_balance: str  # "text_heavy" | "visual_heavy" | "balanced"
    generate_image: bool  # Whether to generate an AI image for this slide
    image_prompt: Optional[
        str
    ]  # Descriptive prompt for image generation (if generate_image is True)


class QAReport(TypedDict):
    approved: bool
    issues: list[dict]  # [{slide_id, severity, description, fix_suggestion}]
    summary: str


class PresentationState(TypedDict):
    company_name: str
    # Agent 1 output
    company_profile: dict
    # Agent 2 output
    slide_plan: list[dict]
    # Agent 3 output
    grounded_plan: list[SlideEvidence]
    # Agent 4 output
    slide_contents: list[SlideContent]
    # Agent 5 output
    qa_report: QAReport
    qa_revision_count: int
    qa_feedback: str
    # Agent 6 output
    design_specs: list[SlideDesignSpec]
    # Image generation output
    image_map: dict  # {slide_id: local_image_path}
    # Renderer output
    pptx_path: str
