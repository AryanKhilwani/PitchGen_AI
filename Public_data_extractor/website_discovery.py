from google import genai
from website_validator import validate_and_canonicalize
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def find_company_website(company_name: str) -> str:
    prompt = f"""
    Find the official website of the company "{company_name}".

    Rules:
    - Return ONLY the website URL
    - Prefer the primary corporate website
    - No explanations
    """

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)

    raw_url = response.text.strip()
    print(f"Raw URL from Gemini: {raw_url}")
    return validate_and_canonicalize(raw_url)
