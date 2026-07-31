"""
ai_service.py
This is the part of Lumé that talks to the Anthropic Claude API.

It is kept in its own file so the AI work is separate from the routes
and from the database, which matches the AIService class in the design.

The main job here is:
  1. build a clear prompt from the user's profile and products,
  2. ask Claude to reply in a fixed JSON format,
  3. read that reply safely and hand it back to the app.
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

# Read the .env file so the API key becomes available.
load_dotenv()

# The API key is read from an environment variable, never written in the code.
# This keeps the secret key out of the source and out of GitHub.
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# We use Haiku: it is fast and low cost, and it is more than enough
# to build a skincare routine.
MODEL = "claude-haiku-4-5-20251001"


def build_prompt(profile, products):
    """Turn the user's data into a clear instruction for the AI.

    profile is the row from the profiles table.
    products is the list of the user's products.
    """
    # Turn the product list into simple text lines.
    if products:
        product_lines = "\n".join(
            f"- {p['name']} ({p['type']})" for p in products
        )
    else:
        product_lines = "The user has not listed any products yet."

    # The prompt has three parts: the role, the user's data, and the
    # rules for the answer. The rules are what keep the reply safe and
    # in a fixed shape.
    prompt = f"""You are a skincare assistant. Build a simple daily routine for this person.

Their profile:
- Skin type: {profile['skin_type']}
- Age: {profile['age']}
- Main concerns: {profile['concerns']}
- Sensitivities: {profile['sensitivities']}
- Allergies: {profile['allergies']}
- Climate: {profile['climate']}

Products they already own:
{product_lines}

Rules you must follow:
- Build the routine around the products they already own where possible.
- You may suggest other product TYPES (not brands) that would help.
- Never suggest anything that contains an ingredient they are allergic to.
- Be careful with ingredients they are sensitive to.
- Only suggest common, safe, over the counter skincare. No medical treatments.
- Give a short, plain reason for each suggestion.

Reply ONLY with JSON in exactly this shape, and nothing else:
{{
  "morning": ["step 1", "step 2"],
  "evening": ["step 1", "step 2"],
  "suggestions": [
    {{"type": "product type", "reason": "short reason"}}
  ]
}}"""
    return prompt


def generate_routine(profile, products):
    """Ask Claude for a routine and return it as a Python dictionary.

    Returns None if anything goes wrong, so the app can show a friendly
    message instead of breaking. This is the 'fail safe' idea.
    """
    prompt = build_prompt(profile, products)

    try:
        # Send the prompt to Claude.
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        # The reply text is inside the response.
        reply_text = response.content[0].text.strip()

        # Sometimes the model wraps JSON in ```json ... ```, so we clean that.
        if reply_text.startswith("```"):
            reply_text = reply_text.strip("`")
            if reply_text.startswith("json"):
                reply_text = reply_text[4:]
            reply_text = reply_text.strip()

        # Turn the JSON text into a Python dictionary.
        routine = json.loads(reply_text)

        # Check the reply has the parts we expect. If not, treat as a failure.
        if "morning" not in routine or "evening" not in routine:
            return None

        return routine

    except Exception as e:
        # Any problem (network, bad JSON, API error) ends up here.
        # We print for our own debugging and return None to the app.
        print("AI routine error:", e)
        return None