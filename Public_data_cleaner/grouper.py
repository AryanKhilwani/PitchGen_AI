from google import genai
import os
from dotenv import load_dotenv
import json
import re
import time

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def group_keys_into_categories(flat_data, max_retries=10):
    """
    Takes the flat merged JSON and uses Gemini to group keys
    under generalized parent categories like Products, Services, etc.
    Returns a dict mapping category names to lists of keys.
    """

    keys = list(flat_data.keys())

    system_prompt = """
You are an expert data organizer. You are given a list of specific JSON keys 
that describe various aspects of a company's data.

Your task: Group these keys under BROAD, GENERALIZED parent categories.

RULES:
1. Create 10-18 broad parent categories (e.g., "Products", "Manufacturing Capabilities", 
   "Services", "Industries Served", "Company Overview", "Testing & Quality Assurance", 
   "Human Resources", "Investor Relations", etc.)
2. Every input key MUST appear in exactly one category.
3. Categories should be intuitive and meaningful for an investor/analyst audience.
4. Use Title Case for category names.
5. Output STRICT VALID JSON mapping each category to a list of keys that belong to it.

Example output format:
{
  "Products": ["industrial_product_offerings", "product_portfolio", "chassis_system_product_offerings"],
  "Manufacturing Capabilities": ["manufacturing_capabilities", "hot_forging_capabilities"],
  "Services": ["engineering_services", "logistics_capabilities"]
}
"""

    prompt = f"""
Here are the keys to categorize:
{json.dumps(keys, indent=2)}

Group them into broad parent categories. Output JSON only.
"""

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=[system_prompt + "\n\n" + prompt],
                config={"temperature": 0.1, "response_mime_type": "application/json"},
            )

            text = response.text.strip()
            text = re.sub(r"^```json", "", text)
            text = re.sub(r"```$", "", text).strip()

            category_map = json.loads(text)

            # Validate: ensure all keys are covered
            mapped_keys = set()
            for cat_keys in category_map.values():
                mapped_keys.update(cat_keys)

            missing = set(keys) - mapped_keys
            if missing:
                print(
                    f"Warning: {len(missing)} keys not categorized, adding to 'Other': {missing}"
                )
                category_map["Other"] = list(missing)

            return category_map

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = 60
                match = re.search(r"retryDelay': '(\d+)s", error_str)
                if match:
                    wait_time = int(match.group(1))
                print(f"Rate limit hit. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue

            print("Grouping failed:", e)
            return None

    print("Max retries reached for grouping.")
    return None


def build_hierarchical_output(flat_data, category_map):
    """
    Restructures flat_data into nested format using the category_map.

    Output: {
      "Products": {
        "industrial_product_offerings": [...],
        "product_portfolio": [...]
      },
      "Manufacturing Capabilities": {
        "manufacturing_capabilities": [...]
      },
      ...
    }
    """
    hierarchical = {}

    for category, keys in category_map.items():
        hierarchical[category] = {}
        for key in keys:
            if key in flat_data:
                hierarchical[category][key] = flat_data[key]

    return hierarchical


def group_flat_data(flat_data):
    """
    Main entry point: takes flat merged data and returns hierarchical grouped data.
    """
    print("Grouping keys into broad categories...")
    category_map = group_keys_into_categories(flat_data)

    if category_map is None:
        print("Grouping failed. Returning flat data as-is.")
        return flat_data

    print(f"Created {len(category_map)} categories:")
    for cat, keys in category_map.items():
        print(f"  {cat}: {len(keys)} sections")

    return build_hierarchical_output(flat_data, category_map)
