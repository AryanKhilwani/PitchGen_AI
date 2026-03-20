"""
Shared state schema for the presentation generation pipeline.

This TypedDict flows through all LangGraph nodes.
Each agent reads what it needs and writes its output fields.

New in v2 (visual grammar):
  - VisualIntent / VisualData   → structured visual contracts per slide
  - DeckTheme                   → full palette + typography + illustration mode
  - SlideComposition            → component-based design spec (replaces fixed layouts)
  Existing types are kept for backward compatibility during migration.
"""

from typing import TypedDict, Optional


# ───────────────────────────────────────────────────────────────
# Legacy types (still consumed by current renderer)
# ───────────────────────────────────────────────────────────────


class ChartableData(TypedDict):
    label: str  # e.g. "Revenue (₹ Cr)"
    data_points: list[dict]  # [{year: "FY13", value: 1200}, ...]
    chart_hint: str  # "line" | "bar" | "pie"


class EvidenceChunk(TypedDict):
    text: str
    score: float
    metadata: dict


# ───────────────────────────────────────────────────────────────
# New: Structured visual data payloads  (Phase 2A)
# ───────────────────────────────────────────────────────────────


class TimelineEvent(TypedDict):
    date: str  # "FY13", "2019-Q3", "1979", etc.
    label: str  # Short event description
    detail: Optional[str]  # Longer explanation (speaker-note level)
    importance: str  # "high" | "medium" | "low"


class ProcessStep(TypedDict):
    order: int  # 1-based sequence number
    label: str  # Step name
    detail: Optional[str]  # Longer explanation


class CycleNode(TypedDict):
    order: int  # Position in the loop (1-based)
    label: str
    detail: Optional[str]


class MatrixCell(TypedDict):
    row: str  # Row header (e.g. "Strengths")
    column: str  # Column header (e.g. "Internal")
    items: list[str]  # Bullet items inside this cell


class HierarchyNode(TypedDict):
    id: str
    label: str
    parent_id: Optional[str]  # None for root
    detail: Optional[str]


class CardItem(TypedDict):
    label: str
    description: Optional[str]
    icon_hint: Optional[str]  # Keyword for icon resolution
    metric: Optional[str]  # Optional numeric highlight


class VisualData(TypedDict, total=False):
    """Structured payloads for each visual component type.

    Only the keys relevant to the chosen visual_type are populated;
    the rest default to empty / None.
    """

    timeline_events: list[TimelineEvent]
    process_steps: list[ProcessStep]
    cycle_nodes: list[CycleNode]
    matrix_cells: list[MatrixCell]
    matrix_row_headers: list[str]
    matrix_col_headers: list[str]
    hierarchy_nodes: list[HierarchyNode]
    card_items: list[CardItem]
    # Chartable data is kept separate for backward compatibility
    chartable_data: list[ChartableData]


class VisualIntent(TypedDict, total=False):
    """Per-slide contract describing what visual the slide should become.

    Emitted by Agent 4 (content) and refined by Agent 6 (design).
    """

    visual_type: str  # Value from VisualComponentType enum
    semantic_trigger: str  # Value from SemanticTrigger enum
    confidence: str  # "high" | "medium" | "low"
    rationale: str  # Why this visual fits the content
    editable_elements: list[str]  # Which parts must stay editable in PPTX
    decorative_elements: list[str]  # Which parts can be pre-rendered images
    visual_data: VisualData  # Structured payload for the chosen visual
    fallback_type: Optional[str]  # VisualComponentType to use if primary fails


# ───────────────────────────────────────────────────────────────
# New: Deck-level theme  (Phase 2A)
# ───────────────────────────────────────────────────────────────


class DeckTheme(TypedDict, total=False):
    """Deck-wide visual identity tokens.

    Generated once by the design agent at the start of a deck,
    then passed to every component renderer.
    """

    primary: str  # Hex — dominant brand color
    secondary: str  # Hex — complementary accent
    surface: str  # Hex — light background for cards / panels
    highlight: str  # Hex — attention / CTA color
    neutral: str  # Hex — muted text / borders
    gradient_start: str  # Hex — gradient left / top
    gradient_end: str  # Hex — gradient right / bottom
    heading_font: str  # e.g. "Montserrat"
    body_font: str  # e.g. "Open Sans"
    illustration_style: str  # e.g. "flat_vector", "isometric"
    density: str  # "compact" | "balanced" | "spacious"


# ───────────────────────────────────────────────────────────────
# New: Component-based slide composition  (Phase 2A)
# ───────────────────────────────────────────────────────────────


class ComponentInstance(TypedDict, total=False):
    """One visual component placed on a slide."""

    component_type: str  # VisualComponentType value
    region: (
        str  # Where on the slide: "full", "left", "right", "top", "bottom", "center"
    )
    prominence: str  # "primary" | "secondary" | "accent"
    visual_data: VisualData  # Data payload for this component
    sizing_priority: int  # Higher = gets more space when competing (1-10)


class SlideComposition(TypedDict, total=False):
    """Component-based design spec for a single slide.

    This replaces the fixed-layout model.  The renderer reads components
    and arranges them using a region/grid engine.
    """

    slide_id: str
    components: list[ComponentInstance]
    visual_intent: VisualIntent
    generate_image: bool
    image_prompt: Optional[str]
    text_hierarchy: dict  # Same format as legacy SlideDesignSpec
    visual_balance: str  # "text_heavy" | "visual_heavy" | "balanced"


# ───────────────────────────────────────────────────────────────
# Legacy: kept for backward compat during migration
# ───────────────────────────────────────────────────────────────


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
    # --- v2 addition (optional until migration complete) ---
    visual_intent: Optional[VisualIntent]


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
    # --- v2 addition (optional until migration complete) ---
    composition: Optional[SlideComposition]


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
    # v2: deck theme (optional until migration complete)
    deck_theme: Optional[DeckTheme]
    # Visual QA output (Phase 6)
    visual_qa_passed: Optional[bool]
    visual_qa_revision_count: int
    # Image generation output
    image_map: dict  # {slide_id: local_image_path}
    # Renderer output
    pptx_path: str
