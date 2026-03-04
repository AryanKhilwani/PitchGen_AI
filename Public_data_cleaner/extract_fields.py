from google import genai
import os
from dotenv import load_dotenv
import json
import re
import time


load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def extract_dynamic_fields(chunk_text, chunk_url, max_retries=10):
    """
    Sends a chunk to Gemini and asks for dynamic JSON categorization.
    """

    system_prompt = """
    You are an expert Investment Analyst AI that extracts structured business intelligence from corporate webpages.

    You are also given the SOURCE URL. Use it to understand page context.

    Example:
    - /investors → financial metrics
    - /products → product offerings
    - /leadership → executives
    - /sustainability → ESG initiatives
    - /press → announcements

    EXTRACTION GOAL
    Extract factual information useful for investors and analysts.

    RULES:
    1. Extract meaningful business information only.
    2. Create descriptive JSON keys dynamically.
    3. Each value MUST be a LIST of COMPLETE factual statements.
    4. Each statement must be self-contained and understandable without the original paragraph.
    5. DO NOT return just keywords or entities.

    GOOD EXAMPLES:
    {
      "forged_products": [
        "The company manufactures cold forged parts.",
        "The company manufactures hot forged parts."
      ],
      "industrial_applications": [
        "The company's forged components are used in power tools.",
        "The company's forged components are used in conveyor systems."
      ]
    }

    BAD EXAMPLES:
    {
      "products": ["cold forged parts", "hot forged parts"],
      "applications": ["power tools", "conveyors"]
    }

    6. Avoid generic keys like info, data, or text.
    7. If no useful information exists return {}.
    8. Output STRICT VALID JSON ONLY.
    """

    prompt = f"""
    SOURCE URL:
    {chunk_url}

    TEXT DATA:
    {chunk_text}

    Extract structured business intelligence in JSON.
    """

    for attempt in range(max_retries):

        try:

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=[system_prompt + "\n\n" + prompt],
                config={"temperature": 0.2, "response_mime_type": "application/json"},
            )

            text = response.text.strip()

            # remove markdown blocks if they appear
            text = re.sub(r"^```json", "", text)
            text = re.sub(r"```$", "", text).strip()

            return json.loads(text)

        except Exception as e:

            error_str = str(e)

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:

                wait_time = 60  # default wait

                # try extracting retryDelay from error message
                match = re.search(r"retryDelay': '(\d+)s", error_str)
                if match:
                    wait_time = int(match.group(1))

                print(f"Rate limit hit. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue

            # other errors
            print("Extraction failed:", e)
            return {}

    print("Max retries reached. Skipping chunk.")
    return {}
