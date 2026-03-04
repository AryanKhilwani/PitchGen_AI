import os
import json
import time
from pathlib import Path
from collections import defaultdict
from chunker import SmartChunker
from Public_data_cleaner.extract_fields import extract_dynamic_fields
from grouper import group_flat_data

# Delay between API calls (seconds) to respect free-tier rate limits
# Free tier: ~15 RPM / ~1M TPM — 5s gap keeps us safely under 12 RPM
API_CALL_DELAY = 5


# -----------------------------
# CONFIG
# -----------------------------

INPUT_JSON = "../Public_data_extractor/outputs/public_data_bundle.json"
OUTPUT_JSON = "outputs/final_structured_data.json"


def load_input(path):
    with open(path, "r") as f:
        return json.load(f)


def merge_results(results):
    """
    Merge LLM extracted JSON outputs into a single dictionary.
    Deduplicates facts.
    """

    merged = defaultdict(set)

    for result in results:

        if not isinstance(result, dict):
            continue

        for key, values in result.items():

            if isinstance(values, list):
                for v in values:
                    merged[key].add(v)

    return {k: sorted(list(v)) for k, v in merged.items()}


def run_pipeline():

    print("Loading cleaned data...")

    cleaned_data = load_input(INPUT_JSON)

    print(f"Loaded {len(cleaned_data)} pages")

    # Chunking
    print("Chunking text...")
    chunker = SmartChunker()

    chunks = chunker.create_chunks(cleaned_data)

    print(f"Created {len(chunks)} chunks")

    extracted_results = []

    # Process each chunk
    for i, chunk in enumerate(chunks):

        print(f"Processing chunk {i+1}/{len(chunks)}")

        try:

            response = extract_dynamic_fields(chunk["text"], chunk["url"])

            parsed = response

            extracted_results.append(parsed)

        except Exception as e:

            print("Chunk failed:", e)

        # Throttle to stay within free-tier rate limits
        if i < len(chunks) - 1:
            time.sleep(API_CALL_DELAY)

    # Merge everything
    print("Merging results...")

    final_data = merge_results(extracted_results)

    # Brief cooldown before grouping call to avoid hitting rate limit
    print("Cooling down before grouping step...")
    time.sleep(API_CALL_DELAY)

    # Group into hierarchical categories
    final_data = group_flat_data(final_data)

    # Save output
    Path(os.path.dirname(OUTPUT_JSON)).mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w") as f:

        json.dump(final_data, f, indent=2)

    print("Pipeline complete")
    print(f"Output saved to {OUTPUT_JSON}")


if __name__ == "__main__":
    run_pipeline()
