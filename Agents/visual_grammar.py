"""
Visual Grammar — Component vocabulary, content-to-visual mapping, and theme system.

This module defines:
  1. The canonical set of visual component types the pipeline can render.
  2. Semantic trigger rules that map content patterns to visual components.
  3. Deck-level theme tokens consumed by the design agent and renderer.

All downstream agents and the renderer import from here so the vocabulary
stays in one place.
"""

from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# 1. Visual Component Types
# ---------------------------------------------------------------------------


class VisualComponentType(str, Enum):
    """Every visual primitive the pipeline can compose onto a slide."""

    # --- Text-centric ---
    HERO_TEXT = "hero_text"  # Large statement / thesis / quote
    BULLET_LIST = "bullet_list"  # Classic icon-bullets
    TEXT_BLOCK = "text_block"  # Paragraph prose (investment thesis)
    QUOTE_CALLOUT = "quote_callout"  # Highlighted quote / tagline card

    # --- Data & metrics ---
    KPI_STRIP = "kpi_strip"  # Row of metric cards (editable)
    CHART_PANEL = "chart_panel"  # Bar / line / pie (editable in PPTX)
    TABLE_PANEL = "table_panel"  # Structured data table (editable)

    # --- Diagrams (hybrid-rendered) ---
    TIMELINE = "timeline"  # Chronological events on a horizontal/vertical axis
    PROCESS_FLOW = "process_flow"  # Ordered steps with directional arrows
    CYCLE_LOOP = "cycle_loop"  # Circular nodes with directional arrows
    COMPARISON_MATRIX = (
        "comparison_matrix"  # Two-axis grid (e.g. SWOT, peer vs metrics)
    )
    HIERARCHY = "hierarchy"  # Org chart / tree structure
    NETWORK_MAP = "network_map"  # Nodes + edges (geography, partnerships)
    VALUE_CHAIN = "value_chain"  # Linear chain of stages (supply chain, process)

    # --- Visual / media ---
    ICON_FACT_GRID = "icon_fact_grid"  # Grid of icon + short fact pairs
    IMAGE_PANEL = "image_panel"  # AI-generated or sourced illustration
    CARD_GRID = "card_grid"  # Portfolio / product card collection

    # --- Modern / Gamma-style compositions ---
    FULL_BLEED_IMAGE = (
        "full_bleed_image"  # Full-slide background image with text overlay
    )
    SPLIT_HERO = "split_hero"  # Asymmetric image + text (e.g. 60/40 image-left)
    STAT_WALL = "stat_wall"  # Large-type stat + supporting context, bold emphasis
    PULL_QUOTE = "pull_quote"  # Editorial-style large quote with attribution
    MEDIA_OVERLAY = "media_overlay"  # Image background with semi-transparent text card

    # --- Structural ---
    SECTION_DIVIDER = "section_divider"  # Branded transition slide


# Subsets used by the renderer to decide native-PPTX vs hybrid path
EDITABLE_NATIVE = {
    VisualComponentType.HERO_TEXT,
    VisualComponentType.BULLET_LIST,
    VisualComponentType.TEXT_BLOCK,
    VisualComponentType.QUOTE_CALLOUT,
    VisualComponentType.KPI_STRIP,
    VisualComponentType.CHART_PANEL,
    VisualComponentType.TABLE_PANEL,
    VisualComponentType.ICON_FACT_GRID,
    VisualComponentType.SECTION_DIVIDER,
    VisualComponentType.STAT_WALL,
    VisualComponentType.PULL_QUOTE,
}

HYBRID_RENDERED = {
    VisualComponentType.TIMELINE,
    VisualComponentType.PROCESS_FLOW,
    VisualComponentType.CYCLE_LOOP,
    VisualComponentType.COMPARISON_MATRIX,
    VisualComponentType.HIERARCHY,
    VisualComponentType.NETWORK_MAP,
    VisualComponentType.VALUE_CHAIN,
    VisualComponentType.CARD_GRID,
    VisualComponentType.IMAGE_PANEL,
    VisualComponentType.FULL_BLEED_IMAGE,
    VisualComponentType.SPLIT_HERO,
    VisualComponentType.MEDIA_OVERLAY,
}


# ---------------------------------------------------------------------------
# 2. Content-to-Visual Mapping Rules  (Phase 1A)
# ---------------------------------------------------------------------------


class SemanticTrigger(str, Enum):
    """Semantic patterns detected in slide content / evidence."""

    CHRONOLOGY = "chronology"  # Dated events, milestones, history
    ORDERED_STEPS = "ordered_steps"  # Numbered / sequential process
    FEEDBACK_LOOP = "feedback_loop"  # Recurring cycle, iterative process
    TWO_AXIS_COMPARE = "two_axis_compare"  # SWOT, pros/cons, peer vs metric
    GROUPED_METRICS = "grouped_metrics"  # 3-6 standalone KPI numbers
    CATEGORY_BREAKDOWN = "category_breakdown"  # Revenue mix, segment share
    ENTITY_RELATIONSHIPS = "entity_relationships"  # Org, partnerships, network
    PORTFOLIO_ITEMS = "portfolio_items"  # Products, services, offerings list
    SINGLE_STATEMENT = "single_statement"  # Thesis, quote, tagline
    NARRATIVE_PROSE = "narrative_prose"  # Investment thesis paragraph
    TIME_SERIES = "time_series"  # Multi-year numeric trend
    TABULAR_DATA = "tabular_data"  # Multi-column structured data
    LINEAR_CHAIN = "linear_chain"  # Supply chain, value chain stages


# Primary mapping: semantic trigger  →  best visual component
TRIGGER_TO_VISUAL: dict[SemanticTrigger, VisualComponentType] = {
    SemanticTrigger.CHRONOLOGY: VisualComponentType.TIMELINE,
    SemanticTrigger.ORDERED_STEPS: VisualComponentType.PROCESS_FLOW,
    SemanticTrigger.FEEDBACK_LOOP: VisualComponentType.CYCLE_LOOP,
    SemanticTrigger.TWO_AXIS_COMPARE: VisualComponentType.COMPARISON_MATRIX,
    SemanticTrigger.GROUPED_METRICS: VisualComponentType.KPI_STRIP,
    SemanticTrigger.CATEGORY_BREAKDOWN: VisualComponentType.CHART_PANEL,
    SemanticTrigger.ENTITY_RELATIONSHIPS: VisualComponentType.NETWORK_MAP,
    SemanticTrigger.PORTFOLIO_ITEMS: VisualComponentType.CARD_GRID,
    SemanticTrigger.SINGLE_STATEMENT: VisualComponentType.HERO_TEXT,
    SemanticTrigger.NARRATIVE_PROSE: VisualComponentType.TEXT_BLOCK,
    SemanticTrigger.TIME_SERIES: VisualComponentType.CHART_PANEL,
    SemanticTrigger.TABULAR_DATA: VisualComponentType.TABLE_PANEL,
    SemanticTrigger.LINEAR_CHAIN: VisualComponentType.VALUE_CHAIN,
}

# Semantic triggers that benefit from bold/modern visual treatment
BOLD_VISUAL_TRIGGERS = {
    SemanticTrigger.SINGLE_STATEMENT,
    SemanticTrigger.GROUPED_METRICS,
}

# Fallback chain: if the primary visual cannot render, try these in order.
VISUAL_FALLBACKS: dict[VisualComponentType, list[VisualComponentType]] = {
    VisualComponentType.TIMELINE: [VisualComponentType.BULLET_LIST],
    VisualComponentType.PROCESS_FLOW: [
        VisualComponentType.ICON_FACT_GRID,
        VisualComponentType.BULLET_LIST,
    ],
    VisualComponentType.CYCLE_LOOP: [
        VisualComponentType.PROCESS_FLOW,
        VisualComponentType.ICON_FACT_GRID,
    ],
    VisualComponentType.COMPARISON_MATRIX: [
        VisualComponentType.TABLE_PANEL,
        VisualComponentType.BULLET_LIST,
    ],
    VisualComponentType.HIERARCHY: [VisualComponentType.BULLET_LIST],
    VisualComponentType.NETWORK_MAP: [VisualComponentType.ICON_FACT_GRID],
    VisualComponentType.VALUE_CHAIN: [
        VisualComponentType.PROCESS_FLOW,
        VisualComponentType.BULLET_LIST,
    ],
    VisualComponentType.CARD_GRID: [
        VisualComponentType.ICON_FACT_GRID,
        VisualComponentType.BULLET_LIST,
    ],
    VisualComponentType.IMAGE_PANEL: [VisualComponentType.ICON_FACT_GRID],
    VisualComponentType.KPI_STRIP: [VisualComponentType.BULLET_LIST],
    VisualComponentType.CHART_PANEL: [
        VisualComponentType.TABLE_PANEL,
        VisualComponentType.BULLET_LIST,
    ],
    VisualComponentType.FULL_BLEED_IMAGE: [VisualComponentType.IMAGE_PANEL],
    VisualComponentType.SPLIT_HERO: [
        VisualComponentType.IMAGE_PANEL,
        VisualComponentType.BULLET_LIST,
    ],
    VisualComponentType.STAT_WALL: [VisualComponentType.KPI_STRIP],
    VisualComponentType.PULL_QUOTE: [VisualComponentType.QUOTE_CALLOUT],
    VisualComponentType.MEDIA_OVERLAY: [
        VisualComponentType.FULL_BLEED_IMAGE,
        VisualComponentType.IMAGE_PANEL,
    ],
}


def resolve_visual(
    trigger: SemanticTrigger,
    hybrid_available: bool = True,
) -> VisualComponentType:
    """Pick the best visual component for a semantic trigger.

    If the primary component requires hybrid rendering and that path is
    unavailable, walk the fallback chain until a native component is found.
    """
    primary = TRIGGER_TO_VISUAL.get(trigger, VisualComponentType.BULLET_LIST)

    if hybrid_available or primary in EDITABLE_NATIVE:
        return primary

    for fallback in VISUAL_FALLBACKS.get(primary, []):
        if fallback in EDITABLE_NATIVE:
            return fallback

    return VisualComponentType.BULLET_LIST


# ---------------------------------------------------------------------------
# 3. Deck Theme Tokens  (consumed by design agent + renderer)
# ---------------------------------------------------------------------------

# Industry → palette presets (expanded from the old single-accent system)
INDUSTRY_THEMES: dict[str, dict] = {
    "automotive": {
        "primary": "#1B3A5C",
        "secondary": "#4A90D9",
        "surface": "#F0F4F8",
        "highlight": "#E8B931",
        "neutral": "#6B7B8D",
        "gradient_start": "#1B3A5C",
        "gradient_end": "#4A90D9",
    },
    "technology": {
        "primary": "#2D5F8A",
        "secondary": "#5BB5E0",
        "surface": "#EEF5FA",
        "highlight": "#00C9A7",
        "neutral": "#7A8B99",
        "gradient_start": "#2D5F8A",
        "gradient_end": "#5BB5E0",
    },
    "pharma": {
        "primary": "#1A7A4C",
        "secondary": "#4CAF50",
        "surface": "#EDF7F0",
        "highlight": "#81C784",
        "neutral": "#6D8B7A",
        "gradient_start": "#1A7A4C",
        "gradient_end": "#4CAF50",
    },
    "logistics": {
        "primary": "#C0571B",
        "secondary": "#F39C12",
        "surface": "#FFF5EB",
        "highlight": "#E67E22",
        "neutral": "#8B7355",
        "gradient_start": "#C0571B",
        "gradient_end": "#F39C12",
    },
    "entertainment": {
        "primary": "#8E44AD",
        "secondary": "#BB6BD9",
        "surface": "#F5EEF8",
        "highlight": "#E74C8B",
        "neutral": "#8B7A99",
        "gradient_start": "#8E44AD",
        "gradient_end": "#BB6BD9",
    },
    "finance": {
        "primary": "#2C3E50",
        "secondary": "#34495E",
        "surface": "#ECF0F1",
        "highlight": "#3498DB",
        "neutral": "#7F8C8D",
        "gradient_start": "#2C3E50",
        "gradient_end": "#3498DB",
    },
    "defense": {
        "primary": "#1B3A5C",
        "secondary": "#C0392B",
        "surface": "#F0F4F8",
        "highlight": "#E74C3C",
        "neutral": "#6B7B8D",
        "gradient_start": "#1B3A5C",
        "gradient_end": "#C0392B",
    },
    "default": {
        "primary": "#2C3E50",
        "secondary": "#3498DB",
        "surface": "#ECF0F1",
        "highlight": "#E74C3C",
        "neutral": "#7F8C8D",
        "gradient_start": "#2C3E50",
        "gradient_end": "#3498DB",
    },
}

# Typography pair presets
FONT_PAIRS: list[dict[str, str]] = [
    {"heading": "Montserrat", "body": "Open Sans", "vibe": "modern_corporate"},
    {"heading": "Playfair Display", "body": "Lato", "vibe": "elegant_editorial"},
    {"heading": "Raleway", "body": "Nunito", "vibe": "light_contemporary"},
    {"heading": "Poppins", "body": "Inter", "vibe": "geometric_tech"},
    {"heading": "Georgia", "body": "Calibri", "vibe": "classic_conservative"},
    {"heading": "Trebuchet MS", "body": "Verdana", "vibe": "friendly_accessible"},
]

# Illustration style options the image-generation agent can target
ILLUSTRATION_STYLES = [
    "flat_vector",  # Clean flat-design illustrations
    "isometric",  # Isometric 3D-style
    "line_art",  # Minimal line drawings
    "gradient_abstract",  # Abstract gradient shapes
    "photorealistic",  # AI photo-style
]


# ---------------------------------------------------------------------------
# 4. Slide Mood & Background Tokens  (Gamma-style visual direction)
# ---------------------------------------------------------------------------

# Slide mood controls the visual weight and atmosphere of each slide.
# The design agent assigns one mood per slide; the renderer uses it.
SLIDE_MOODS = [
    "bold",  # Dark background, large type, high contrast — hero moments
    "light",  # White/surface background, clean spacing — default evidence slides
    "editorial",  # Image-forward, text overlay, magazine-like — story moments
    "data",  # Neutral background, data-viz dominant — charts & tables
    "accent",  # Gradient or brand-colored background — section dividers
]

# Background treatment types the design agent can assign per slide.
BACKGROUND_TREATMENTS = [
    "solid_surface",  # Plain surface color (default)
    "gradient_brand",  # Primary→secondary gradient (good for bold/accent)
    "full_bleed_image",  # AI image covers entire slide, text overlaid
    "split_image",  # Image fills one side, solid color on the other
    "dark_solid",  # Dark primary color, white text (bold mood)
    "subtle_pattern",  # Surface color + faint dot/circle pattern motif
]

# Asymmetric region presets — alternatives to the default balanced splits.
ASYMMETRIC_PRESETS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "hero_left_40": {
        "hero": (0.0, 0.0, 5.6, 7.5),  # Image fills left 42%
        "content": (6.1, 1.2, 6.7, 5.8),  # Text on right 58%
    },
    "hero_right_40": {
        "content": (0.5, 1.2, 6.7, 5.8),  # Text on left 58%
        "hero": (7.7, 0.0, 5.633, 7.5),  # Image fills right 42%
    },
    "hero_left_60": {
        "hero": (0.0, 0.0, 8.0, 7.5),  # Image fills left 60%
        "content": (8.5, 1.5, 4.3, 5.0),  # Narrow text column right
    },
    "cinematic_top": {
        "hero": (0.0, 0.0, 13.333, 4.5),  # Image fills top 60%
        "content": (0.8, 5.0, 11.7, 2.2),  # Text bar at bottom
    },
    "stat_focus": {
        "stat": (0.5, 1.0, 12.3, 3.5),  # Big stat in upper 2/3
        "context": (0.5, 5.0, 12.3, 2.0),  # Supporting text below
    },
}


def resolve_industry_theme(industry: str) -> dict:
    """Return the best-matching theme palette for an industry string."""
    key = industry.lower().strip()
    for theme_key in INDUSTRY_THEMES:
        if theme_key in key or key in theme_key:
            return INDUSTRY_THEMES[theme_key]
    return INDUSTRY_THEMES["default"]
