"""
Image Generator — Executes image generation requests from the Design Agent.

The Slide Design Agent decides WHICH slides get images and provides
the image prompts. This module simply executes those requests via
Gemini Imagen and returns a mapping of slide_id → image_path.
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

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


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
        print(f"  Generating image for [{sid}]...")
        print(f"    Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = client.models.generate_images(
                    model=IMAGEN_MODEL,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="16:9",
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
