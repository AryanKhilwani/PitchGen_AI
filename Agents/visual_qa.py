"""
Visual QA — Post-design check for layout variety, composition quality,
and visual balance. Runs after Agent 6 (slide_design) and before image
generation. Can re-route back to slide_design if the deck is visually
monotonous or has composition issues.

This is a deterministic check (no LLM call) to keep it fast.
"""

from Agents.state import PresentationState

# Maximum visual QA loops before proceeding
MAX_VISUAL_QA_REVISIONS = 2


def _score_visual_variety(design_specs: list) -> list[dict]:
    """Score the deck's visual variety and return issues."""
    issues = []

    # Collect layout and composition info
    layouts = []
    comp_types_per_slide = []
    image_count = 0
    moods = []
    bg_treatments = []

    for spec in design_specs:
        layouts.append(spec.get("layout", "title_content"))
        comps = (spec.get("composition") or {}).get("components", [])
        types = [c.get("type", "") for c in comps]
        comp_types_per_slide.append(types)
        if spec.get("generate_image"):
            image_count += 1
        moods.append(spec.get("slide_mood", "light"))
        bg_treatments.append(spec.get("background_treatment", "solid_surface"))

    n = len(design_specs)

    # --- Check 1: Layout monotony (3+ consecutive identical layouts) ---
    for i in range(len(layouts) - 2):
        if layouts[i] == layouts[i + 1] == layouts[i + 2]:
            if layouts[i] not in ("title_slide",):  # title_slide repeats are rare
                issues.append(
                    {
                        "type": "layout_monotony",
                        "severity": "warning",
                        "detail": (
                            f"Slides {i+1}–{i+3} all use '{layouts[i]}' layout. "
                            f"Consider varying with a section_header, chart_slide, "
                            f"or composition-based layout."
                        ),
                    }
                )
                break

    # --- Check 2: No compositions at all (all legacy layouts) ---
    slides_with_comp = sum(1 for types in comp_types_per_slide if types)
    if n >= 5 and slides_with_comp == 0:
        issues.append(
            {
                "type": "no_compositions",
                "severity": "critical",
                "detail": (
                    "No slides use component compositions. The deck will render "
                    "entirely with legacy layouts. Add timeline, kpi_strip, "
                    "process_flow, or card_grid compositions."
                ),
            }
        )

    # --- Check 3: Component type diversity ---
    all_types = set()
    for types in comp_types_per_slide:
        all_types.update(types)
    # Remove generic types that don't count toward variety
    visual_types = all_types - {"bullet_list", "text_block", "hero_text"}
    if n >= 6 and len(visual_types) <= 1:
        issues.append(
            {
                "type": "low_component_diversity",
                "severity": "warning",
                "detail": (
                    f"Only {len(visual_types)} distinct visual component types "
                    f"across {n} slides (excluding text). Add variety: timeline, "
                    f"kpi_strip, process_flow, comparison_matrix, card_grid."
                ),
            }
        )

    # --- Check 4: Image distribution ---
    if n >= 8 and image_count == 0:
        issues.append(
            {
                "type": "no_images",
                "severity": "warning",
                "detail": (
                    "No slides have AI-generated images. Consider adding hero "
                    "visuals to 2–4 slides (cover, overview, market, thesis)."
                ),
            }
        )
    elif image_count > n * 0.6:
        issues.append(
            {
                "type": "too_many_images",
                "severity": "info",
                "detail": (
                    f"{image_count}/{n} slides have images — this may slow "
                    f"generation. Target 3–5 images per deck."
                ),
            }
        )

    # --- Check 5: Missing section dividers between topic clusters ---
    # Simple heuristic: if deck has 10+ slides and 0 section_headers/dividers
    has_divider = any(
        l in ("section_header",) or any(t == "section_divider" for t in types)
        for l, types in zip(layouts, comp_types_per_slide)
    )
    if n >= 10 and not has_divider:
        issues.append(
            {
                "type": "no_section_dividers",
                "severity": "info",
                "detail": (
                    "Deck has 10+ slides but no section dividers. Consider adding "
                    "section_header slides between major topic transitions."
                ),
            }
        )

    # --- Check 6: Hero moments (bold/editorial moods) ---
    hero_moods = sum(1 for m in moods if m in ("bold", "editorial"))
    if n >= 6 and hero_moods == 0:
        issues.append(
            {
                "type": "no_hero_moments",
                "severity": "warning",
                "detail": (
                    "No slides use 'bold' or 'editorial' mood. The deck lacks "
                    "visual hero moments. Use bold mood for key thesis, stats, "
                    "or closing slides; editorial for image-forward storytelling."
                ),
            }
        )

    # --- Check 7: Mood monotony (4+ consecutive identical moods) ---
    for i in range(len(moods) - 3):
        if moods[i] == moods[i + 1] == moods[i + 2] == moods[i + 3]:
            issues.append(
                {
                    "type": "mood_monotony",
                    "severity": "warning",
                    "detail": (
                        f"Slides {i+1}–{i+4} all use '{moods[i]}' mood. "
                        f"Alternate between bold/editorial and light/data "
                        f"for visual rhythm."
                    ),
                }
            )
            break

    # --- Check 8: Modern component usage ---
    modern_types = {
        "full_bleed_image",
        "split_hero",
        "stat_wall",
        "pull_quote",
        "media_overlay",
    }
    all_types_flat = set()
    for types in comp_types_per_slide:
        all_types_flat.update(types)
    modern_used = all_types_flat & modern_types
    if n >= 8 and len(modern_used) == 0:
        issues.append(
            {
                "type": "no_modern_components",
                "severity": "info",
                "detail": (
                    "No modern visual components used (full_bleed_image, split_hero, "
                    "stat_wall, pull_quote). Consider adding 2–3 for a contemporary feel."
                ),
            }
        )

    # --- Check 9: Background treatment variety ---
    unique_treatments = set(bg_treatments)
    if n >= 8 and len(unique_treatments) <= 1:
        issues.append(
            {
                "type": "bg_monotony",
                "severity": "info",
                "detail": (
                    f"All slides use '{bg_treatments[0]}' background. Mix in "
                    f"gradient_brand, dark_solid, or full_bleed_image for visual interest."
                ),
            }
        )

    return issues


def run(state: PresentationState) -> dict:
    """
    LangGraph node function (deterministic — no LLM).
    Checks design specs for visual variety and balance.
    """
    design_specs = state["design_specs"]
    revision_count = state.get("visual_qa_revision_count", 0)

    print(f"\n{'='*60}")
    print(f"[Visual QA] Checking design variety (pass {revision_count + 1})")
    print(f"{'='*60}")

    issues = _score_visual_variety(design_specs)

    critical = sum(1 for i in issues if i.get("severity") == "critical")
    warnings = sum(1 for i in issues if i.get("severity") == "warning")
    info = sum(1 for i in issues if i.get("severity") == "info")

    passed = critical == 0 and warnings <= 1

    for issue in issues:
        sev = issue["severity"].upper()
        print(f"  [{sev}] {issue['detail']}")

    if not issues:
        print("  ✓ Visual variety looks good.")

    print(
        f"  Result: {'PASS' if passed else 'NEEDS REVISION'} "
        f"({critical} critical, {warnings} warning, {info} info)"
    )

    # Build feedback for slide_design re-run
    qa_feedback = ""
    if not passed:
        parts = [
            f"[VISUAL QA {i['severity'].upper()}] {i['detail']}"
            for i in issues
            if i["severity"] in ("critical", "warning")
        ]
        qa_feedback = "\n".join(parts)

    return {
        "visual_qa_passed": passed,
        "visual_qa_revision_count": revision_count + 1,
        "qa_feedback": state.get("qa_feedback", "")
        + ("\n\n--- VISUAL QA FEEDBACK ---\n" + qa_feedback if qa_feedback else ""),
    }
