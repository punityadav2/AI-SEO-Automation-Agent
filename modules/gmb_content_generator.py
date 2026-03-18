"""
modules/gmb_content_generator.py — Module 3b: GMB Post + Content Generator
- Generates Google My Business posts using Groq API
- Includes NAP consistency check (Name, Address, Phone)
- Publishes post via GMB API (My Business API v4.9) if credentials available
- Localised keywords + city-specific content
"""

import json
import os
import time
import random
import requests
from groq import Groq
from google.oauth2 import service_account
from googleapiclient.discovery import build

import config
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger(__name__)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

# GMB API scope
GMB_SCOPES = ["https://www.googleapis.com/auth/business.manage"]
GMB_API_VERSION = "v4"
GMB_API_SERVICE  = "mybusiness"


def _get_gmb_service():
    """Build authenticated GMB API service from service account JSON."""
    creds_path = "service_account.json"
    if not os.path.exists(creds_path):
        logger.warning("service_account.json not found — GMB API calls will be skipped.")
        return None
    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=GMB_SCOPES
    )
    service = build(
        GMB_API_SERVICE,
        GMB_API_VERSION,
        credentials=creds,
        discoveryServiceUrl=(
            "https://mybusinessaccountmanagement.googleapis.com/$discovery/rest?version=v1"
        ),
    )
    return service


@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _generate_gmb_post(keyword: str, city: str, nap_info: dict) -> dict:
    """
    Generate a GMB-optimised post using Groq.
    Includes localised keyword, NAP consistency, and CTA.
    """
    client = Groq(api_key=config.GROQ_API_KEY)

    prompt = f"""Write a Google My Business post for a business targeting customers in {city}.

Target keyword: "{keyword} in {city}"
Business Name: {nap_info.get('name', 'Our Business')}
City: {city}
Industry: {config.TARGET_INDUSTRY}

Requirements:
- Length: 150-300 words (GMB optimal range)
- Open with a local angle (mention {city} naturally)
- Include the keyword "{keyword}" naturally (1-2 times)
- End with ONE clear call-to-action
- Professional but warm tone
- Do NOT use generic filler phrases

Also suggest:
- CTA button type (BOOK / CALL / LEARN_MORE / ORDER / SHOP)

Return ONLY JSON:
{{
  "post_body": "...",
  "cta_type": "LEARN_MORE",
  "cta_url": "https://yourdomain.com",
  "keyword_used": "{keyword} in {city}",
  "local_signal": "Describe which local element you included"
}}"""

    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a local SEO expert specialising in GMB. Return only valid JSON."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.7,
        max_tokens=600,
    )
    raw = response.choices[0].message.content.strip()

    try:
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception:
        logger.warning("GMB post JSON parse error — returning raw text.")
        return {
            "post_body": raw,
            "cta_type": "LEARN_MORE",
            "cta_url": "https://yourdomain.com",
            "keyword_used": keyword,
            "local_signal": "City mentioned",
        }


@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _publish_to_gmb(service, post_data: dict) -> dict:
    """
    Publish a post to GMB via the My Business API.
    Requires GMB_ACCOUNT_ID and GMB_LOCATION_ID in .env.
    """
    if not service or not config.GMB_ACCOUNT_ID or not config.GMB_LOCATION_ID:
        logger.warning("GMB credentials not set — skipping publish.")
        return {"status": "skipped", "reason": "credentials not configured"}

    parent = f"{config.GMB_ACCOUNT_ID}/{config.GMB_LOCATION_ID}"

    body = {
        "languageCode": "en",
        "summary":      post_data["post_body"],
        "callToAction": {
            "actionType": post_data.get("cta_type", "LEARN_MORE"),
            "url":        post_data.get("cta_url", ""),
        },
    }

    result = service.accounts().locations().localPosts().create(
        parent=parent,
        body=body
    ).execute()

    logger.info(f"  GMB post published: {result.get('name', 'unknown')}")
    return {"status": "published", "gmb_post_name": result.get("name")}


# ── Main public function ──────────────────────────────────────────────────────
def run(keyword: str, nap_info: dict = None) -> dict:
    """
    Generate and (optionally) publish a GMB post.

    Args:
        keyword  : Target keyword (will be localised).
        nap_info : Dict with 'name', 'address', 'phone' for NAP consistency.

    Returns:
        Dict with post content + publish status.
    """
    logger.info(f"▶ GMB Content Generation | keyword='{keyword}' | city='{config.TARGET_CITY}'")

    if nap_info is None:
        nap_info = {
            "name":    "Your Business Name",
            "address": f"{config.TARGET_CITY}",
            "phone":   "+91 00000 00000",
        }

    post_data = _generate_gmb_post(keyword, config.TARGET_CITY, nap_info)

    # Attempt GMB API publish
    service = _get_gmb_service()
    publish_result = _publish_to_gmb(service, post_data)

    output = {
        "keyword":        keyword,
        "city":           config.TARGET_CITY,
        "nap_info":       nap_info,
        "gmb_post":       post_data,
        "publish_result": publish_result,
    }

    out_path = os.path.join(config.OUTPUT_DIR, "gmb_post.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ GMB content saved → {out_path} | Status: {publish_result.get('status')}")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    args = parser.parse_args()
    result = run(args.keyword)
    print(f"\nGMB Post Generated:\n{result['gmb_post']['post_body'][:300]}…")
