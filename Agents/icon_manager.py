"""
Icon Manager — Renders Lucide icons as accent-tinted PNGs for PPTX embedding.

Bundles SVG path data from Lucide (MIT License — https://lucide.dev)
and converts to PNG using cairosvg. Falls back gracefully if cairosvg
is unavailable (renderer will use emoji instead).
"""

import os
from pathlib import Path

ICON_CACHE_DIR = Path(__file__).parent / "assets" / "icons"

# ---------------------------------------------------------------------------
# Lucide SVG inner paths (MIT License)
# Source: https://github.com/lucide-icons/lucide
# Each value is the SVG inner elements (everything inside the <svg> tag).
# ---------------------------------------------------------------------------
LUCIDE_ICONS = {
    "trending-up": (
        '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
        '<polyline points="16 7 22 7 22 13"/>'
    ),
    "dollar-sign": (
        '<line x1="12" x2="12" y1="2" y2="22"/>'
        '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
    ),
    "bar-chart-3": (
        '<path d="M3 3v18h18"/>'
        '<path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>'
    ),
    "activity": (
        '<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36'
        "a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35"
        ' 8.36A2 2 0 0 1 4.49 12H2"/>'
    ),
    "building-2": (
        '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/>'
        '<path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/>'
        '<path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/>'
        '<path d="M10 6h4"/><path d="M10 10h4"/>'
        '<path d="M10 14h4"/><path d="M10 18h4"/>'
    ),
    "briefcase": (
        '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>'
        '<rect width="20" height="14" x="2" y="6" rx="2"/>'
    ),
    "users": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "crown": (
        '<path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0'
        " 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0"
        " 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1"
        ' .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z"/>'
        '<path d="M5.21 16.5h13.58"/>'
    ),
    "factory": (
        '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7'
        ' 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/>'
        '<path d="M17 18h1"/><path d="M12 18h1"/><path d="M7 18h1"/>'
    ),
    "package": (
        '<path d="m7.5 4.27 9 5.15"/>'
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2'
        " 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2"
        ' 2 0 0 0 21 16Z"/>'
        '<path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>'
    ),
    "truck": (
        '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/>'
        '<path d="M15 18H9"/>'
        '<path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624'
        'l-3.48-4.35A1 1 0 0 0 17.52 8H14"/>'
        '<circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>'
    ),
    "lightbulb": (
        '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6'
        ' 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>'
        '<path d="M9 18h6"/><path d="M10 22h4"/>'
    ),
    "sparkles": (
        '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5'
        " 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5"
        ".5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581"
        "a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582"
        ' 6.135a.5.5 0 0 1-.963 0z"/>'
        '<path d="M20 3v4"/><path d="M22 5h-4"/>'
    ),
    "microscope": (
        '<path d="M6 18h8"/><path d="M3 22h18"/>'
        '<path d="M14 22a7 7 0 1 0 0-14h-1"/>'
        '<path d="M9 14h2"/>'
        '<path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z"/>'
        '<path d="M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3"/>'
    ),
    "triangle-alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0'
        ' 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "shield": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5'
        " 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17"
        ' 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
    ),
    "shield-check": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5'
        " 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17"
        ' 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    "scale": (
        '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>'
        '<path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/>'
        '<path d="M7 21h10"/><path d="M12 3v18"/>'
        '<path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>'
    ),
    "clipboard-check": (
        '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/>'
        '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0'
        ' 1-2-2V6a2 2 0 0 1 2-2h2"/>'
        '<path d="m9 14 2 2 4-4"/>'
    ),
    "circle-check": ('<circle cx="12" cy="12" r="10"/>' '<path d="m9 12 2 2 4-4"/>'),
    "zap": (
        '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1'
        " .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63"
        'l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>'
    ),
    "trophy": (
        '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>'
        '<path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>'
        '<path d="M4 22h16"/>'
        '<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7'
        ' 20.24 7 22"/>'
        '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17'
        ' 20.24 17 22"/>'
        '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>'
    ),
    "star": (
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18'
        ' 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
    ),
    "key": (
        '<circle cx="7.5" cy="15.5" r="5.5"/>'
        '<path d="m21 2-9.6 9.6"/>'
        '<path d="m15.5 7.5 3 3L22 7l-3-3"/>'
    ),
    "target": (
        '<circle cx="12" cy="12" r="10"/>'
        '<circle cx="12" cy="12" r="6"/>'
        '<circle cx="12" cy="12" r="2"/>'
    ),
    "crosshair": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M22 12h-4"/><path d="M6 12H2"/>'
        '<path d="M12 6V2"/><path d="M12 22v-4"/>'
    ),
    "globe": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>'
        '<path d="M2 12h20"/>'
    ),
    "rocket": (
        '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84'
        '.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>'
        '<path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1'
        ' 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>'
        '<path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>'
        '<path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>'
    ),
    "swords": (
        '<polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/>'
        '<line x1="13" x2="19" y1="19" y2="13"/>'
        '<line x1="16" x2="20" y1="16" y2="20"/>'
        '<line x1="19" x2="21" y1="21" y2="19"/>'
        '<polyline points="14.5 6.5 18 3 21 3 21 6 17.5 9.5"/>'
        '<line x1="5" x2="9" y1="14" y2="18"/>'
        '<line x1="7" x2="4" y1="17" y2="20"/>'
        '<line x1="3" x2="5" y1="19" y2="21"/>'
    ),
    "arrow-right": ('<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>'),
    "info": (
        '<circle cx="12" cy="12" r="10"/>' '<path d="M12 16v-4"/><path d="M12 8h.01"/>'
    ),
    "file-text": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2'
        ' 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>'
    ),
    "clock": (
        '<circle cx="12" cy="12" r="10"/>' '<polyline points="12 6 12 12 16 14"/>'
    ),
    "calendar": (
        '<path d="M8 2v4"/><path d="M16 2v4"/>'
        '<rect width="18" height="18" x="3" y="4" rx="2"/>'
        '<path d="M3 10h18"/>'
    ),
    "flag": (
        '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2'
        '-4 1-4 1z"/>'
        '<line x1="4" x2="4" y1="22" y2="15"/>'
    ),
    "map-pin": (
        '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>'
        '<circle cx="12" cy="10" r="3"/>'
    ),
    "handshake": (
        '<path d="m11 17 2 2a1 1 0 1 0 3-3"/>'
        '<path d="m14 14 2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0'
        " 0-4.24 0l-.88.88a1 1 0 1 1-3-3l2.81-2.81a5.79 5.79 0 0 1"
        ' 7.06-.87l.47.28a2 2 0 0 0 1.42.25L21 4"/>'
        '<path d="m21 3 1 11h-2"/>'
        '<path d="M3 3 2 14l6.5 6.5a1 1 0 1 0 3-3"/>'
        '<path d="M3 4h8"/>'
    ),
    "muscle": (  # "biceps" isn't in Lucide; use zap for "strength"
        '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1'
        " .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63"
        'l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>'
    ),
    "compass": (
        '<circle cx="12" cy="12" r="10"/>'
        '<polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>'
    ),
}

# ---------------------------------------------------------------------------
# Keyword → Lucide icon name mapping
# ---------------------------------------------------------------------------
KEYWORD_TO_ICON = {
    # Financial / Growth
    "growth": "trending-up",
    "trending_up": "trending-up",
    "revenue": "dollar-sign",
    "profit": "dollar-sign",
    "financial": "bar-chart-3",
    "chart": "bar-chart-3",
    "performance": "activity",
    "money": "dollar-sign",
    # Corporate
    "building": "building-2",
    "company": "building-2",
    "corporate": "briefcase",
    "office": "building-2",
    "team": "users",
    "people": "users",
    "management": "users",
    "leadership": "crown",
    # Product / Industry
    "factory": "factory",
    "manufacturing": "factory",
    "product": "package",
    "supply": "truck",
    "technology": "lightbulb",
    "innovation": "sparkles",
    "idea": "lightbulb",
    "research": "microscope",
    # Risk / Governance
    "risk": "triangle-alert",
    "warning": "triangle-alert",
    "shield": "shield",
    "security": "shield-check",
    "governance": "scale",
    "compliance": "clipboard-check",
    "regulation": "clipboard-check",
    # Positive / Achievement
    "check": "circle-check",
    "success": "circle-check",
    "strength": "zap",
    "advantage": "trophy",
    "star": "star",
    "highlight": "star",
    "key": "key",
    "award": "trophy",
    "target": "target",
    "goal": "target",
    "strategy": "compass",
    "focus": "crosshair",
    # Market / Global
    "market": "globe",
    "global": "globe",
    "world": "globe",
    "expansion": "rocket",
    "competitor": "swords",
    "peer": "bar-chart-3",
    "benchmark": "bar-chart-3",
    # General
    "arrow": "arrow-right",
    "next": "arrow-right",
    "info": "info",
    "note": "file-text",
    "timeline": "clock",
    "history": "calendar",
    "milestone": "flag",
    "location": "map-pin",
    "client": "handshake",
    "partner": "handshake",
}

# SVG wrapper template
_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}"'
    ' viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
)

# Cache rendered availability flag so we only warn once
_cairosvg_available = None


def _check_cairosvg():
    global _cairosvg_available
    if _cairosvg_available is None:
        try:
            import cairosvg  # noqa: F401

            _cairosvg_available = True
        except ImportError:
            _cairosvg_available = False
            print("  [Icon Manager] cairosvg not installed — using emoji fallback.")
            print("  Install for Lucide icons: pip install cairosvg")
    return _cairosvg_available


def get_icon_png(keyword: str, color_hex: str = "2C3E50", size: int = 96) -> str | None:
    """
    Get path to a tinted PNG icon for the given keyword.
    Returns None if cairosvg is unavailable or keyword not recognized.
    """
    if not _check_cairosvg():
        return None

    keyword_clean = keyword.lower().strip()
    icon_name = KEYWORD_TO_ICON.get(keyword_clean)
    if not icon_name or icon_name not in LUCIDE_ICONS:
        # Try partial matching
        for map_key, name in KEYWORD_TO_ICON.items():
            if keyword_clean in map_key or map_key in keyword_clean:
                icon_name = name
                break
        if not icon_name:
            return None

    # Normalize color
    color_hex = color_hex.lstrip("#")
    if len(color_hex) != 6:
        color_hex = "2C3E50"

    # Check cache
    cache_path = ICON_CACHE_DIR / f"{icon_name}_{color_hex}_{size}.png"
    if cache_path.exists():
        return str(cache_path)

    # Build SVG
    svg_content = _SVG_TEMPLATE.format(
        size=size,
        color=f"#{color_hex}",
        paths=LUCIDE_ICONS[icon_name],
    )

    # Convert SVG → PNG
    try:
        import cairosvg

        ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            write_to=str(cache_path),
            output_width=size,
            output_height=size,
        )
        return str(cache_path)
    except Exception as e:
        print(f"  [Icon Manager] Failed to render '{icon_name}': {e}")
        return None


def resolve_icon_for_bullet(
    icon_hints: list, bullet_index: int, accent_hex: str, size: int = 96
) -> str | None:
    """
    Resolve and render the icon PNG for a specific bullet point.
    Cycles through icon_hints for variety across bullets.
    Returns a file path to the PNG, or None for emoji fallback.
    """
    if not icon_hints:
        return None

    # Cycle through hints for visual variety
    hint = icon_hints[bullet_index % len(icon_hints)]
    return get_icon_png(hint, accent_hex, size)
