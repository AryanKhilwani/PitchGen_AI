"""
Image Generator — Executes image generation requests from the Design Agent.

The Slide Design Agent decides WHICH slides get images and provides
the image prompts. This module simply executes those requests via
Gemini Imagen and returns a mapping of slide_id → image_path.

Aspect ratio is chosen dynamically based on how the image will be
placed on the slide (layout, composition, image_panel region, etc.).
"""

import os
import sys
import base64
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "RAG", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from google import genai
from google.genai import types

from Agents.state import PresentationState


# Directory for generated images
IMAGE_DIR = os.path.join("Agents", "outputs", "images")

# Imagen model
IMAGEN_MODEL = "imagen-4.0-generate-001"

# Supported Imagen aspect ratios
VALID_RATIOS = {"1:1", "3:4", "4:3", "9:16", "16:9"}

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


def _choose_aspect_ratio(spec: dict) -> str:
    """Pick the best Imagen aspect ratio for a slide's image placement.

    Decision tree:
      1. If the spec explicitly provides image_aspect_ratio, use it.
      2. If the composition has an image_panel → 16:9 (full landscape hero).
      3. If composition has side_note region alongside main → 3:4 (vertical,
         since the image gets tucked into a narrow right/bottom pocket).
      4. title_slide layout → 3:4 (tall hero on the right half).
      5. two_column layout → 1:1 (fits a square column area).
      6. title_content with image → 4:3 (landscape supplemental on right).
      7. Default → 16:9 (landscape).
    """
    # 1. Explicit override from design agent
    explicit = spec.get("image_aspect_ratio", "")
    if explicit in VALID_RATIOS:
        return explicit

    layout = spec.get("layout", "title_content")
    composition = spec.get("composition") or {}
    components = composition.get("components", [])
    comp_types = {c.get("type", "") for c in components}
    comp_regions = {c.get("region", "") for c in components}

    # 2. image_panel present → full landscape hero
    if "image_panel" in comp_types:
        return "16:9"

    # 3. side_note alongside main → image will go vertical/small
    if "side_note" in comp_regions and "main" in comp_regions:
        return "3:4"

    # 4. title_slide / cover → tall hero image on right
    if layout == "title_slide":
        return "3:4"

    # 5. two_column → square fits both halves
    if layout == "two_column":
        return "1:1"

    # 6. section_header → wide atmospheric background
    if layout in ("section_header", "blank"):
        return "16:9"

    # 7. title_content (standard) → landscape supplemental
    if layout == "title_content":
        return "4:3"

    # 8. Default
    return "16:9"


def generate_images_for_slides(state: PresentationState) -> dict:
    """
    LangGraph node function.
    Reads design_specs for slides where generate_image=True,
    uses the agent-provided image_prompt, and generates images.
    Returns image_map: {slide_id: image_path}.
    """
    company_name = state["company_name"]
    design_specs = state["design_specs"]

    print(f"\n{'='*60}")
    print(f"[Image Gen] Generating slide images — {company_name}")
    print(f"{'='*60}")

    os.makedirs(IMAGE_DIR, exist_ok=True)
    safe_name = company_name.replace(" ", "_").replace("/", "-")

    image_map = {}
    client = _get_client()

    # Collect slides where the design agent requested image generation
    slides_to_generate = []
    for spec in design_specs:
        if spec.get("generate_image") and spec.get("image_prompt"):
            slides_to_generate.append(spec)

    print(
        f"  Slides requesting images: {len(slides_to_generate)} / {len(design_specs)}"
    )

    for spec in slides_to_generate:
        sid = spec["slide_id"]
        prompt = spec["image_prompt"]
        ratio = _choose_aspect_ratio(spec)
        print(f"  Generating image for [{sid}] (aspect_ratio={ratio})...")
        print(f"    Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = client.models.generate_images(
                    model=IMAGEN_MODEL,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=ratio,
                        safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    ),
                )

                if response.generated_images:
                    img_data = response.generated_images[0].image.image_bytes
                    img_path = os.path.join(IMAGE_DIR, f"{safe_name}_{sid}.png")
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    image_map[sid] = img_path
                    print(f"    ✓ Saved: {img_path}")
                else:
                    print(f"    ✗ No image returned for [{sid}]")
                break  # success or empty — don't retry

            except Exception as e:
                err = str(e)
                is_transient = any(
                    p in err.lower()
                    for p in (
                        "429",
                        "503",
                        "500",
                        "unavailable",
                        "overloaded",
                        "resource_exhausted",
                        "high demand",
                        "try again",
                    )
                )
                if is_transient and attempt < max_retries - 1:
                    wait = min(30 * (2**attempt), 180)  # 30, 60, 120, 180
                    print(
                        f"    ⏳ Transient error (attempt {attempt+1}/{max_retries}): "
                        f"{err[:80]}..."
                    )
                    print(f"       Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    ✗ Error generating image for [{sid}]: {e}")
                    break

        # Rate limit: Imagen has strict rate limits on free tier
        time.sleep(2)

    print(f"\n  Images generated: {len(image_map)} / {len(slides_to_generate)}")
    return {"image_map": image_map}
