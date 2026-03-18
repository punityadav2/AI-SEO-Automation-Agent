"""
modules/competitor_analysis.py — Module 2: Competitor Gap Analysis
- Scrapes top-ranking competitor pages (H1/H2/H3 extraction)
- Sends headings to Groq LLM to identify missing content angles
- Returns structured content gap opportunities
"""

import json
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from groq import Groq

import config
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger(__name__)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


# ── Scrape a single competitor URL ────────────────────────────────────────────
@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _scrape_page(url: str) -> dict:
    """
    Scrape a competitor URL and extract headings + meta.
    Returns dict with url, title, meta_desc, headings list, word_count.
    """
    logger.info(f"  Scraping: {url}")
    time.sleep(random.uniform(config.DELAY_MIN_SECS, config.DELAY_MAX_SECS))

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"  Failed to fetch {url}: {exc}")
        return {"url": url, "headings": [], "title": "", "meta_desc": "", "word_count": 0}

    soup = BeautifulSoup(resp.text, "lxml")

    # Extract headings
    headings = []
    for tag in ["h1", "h2", "h3"]:
        for el in soup.find_all(tag):
            text = el.get_text(strip=True)
            if text:
                headings.append({"level": tag.upper(), "text": text})

    # Meta info
    title_el    = soup.find("title")
    meta_el     = soup.find("meta", attrs={"name": "description"})
    body_text   = soup.get_text(separator=" ", strip=True)
    word_count  = len(body_text.split())

    return {
        "url":       url,
        "title":     title_el.get_text(strip=True) if title_el else "",
        "meta_desc": meta_el["content"] if meta_el and meta_el.get("content") else "",
        "headings":  headings,
        "word_count": word_count,
    }


# ── Groq LLM: generate gap analysis ──────────────────────────────────────────
@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _analyze_gaps_with_groq(keyword: str, scraped_pages: list[dict]) -> list[dict]:
    """Send competitor headings to Groq and return structured content gaps."""
    client = Groq(api_key=config.GROQ_API_KEY)

    # Build heading summary for the prompt
    heading_summary = ""
    for page in scraped_pages:
        heading_summary += f"\n\nURL: {page['url']}\n"
        for h in page["headings"][:20]:   # limit to 20 headings per page
            heading_summary += f"  {h['level']}: {h['text']}\n"

    prompt = f"""You are an expert SEO strategist. I'm targeting the keyword: "{keyword}".

Here are the headings from the top-ranking competitor pages:
{heading_summary}

Analyze these competitor pages and identify EXACTLY 5 specific content angles these competitors have MISSED or underexplored. 
These should be genuine gaps a reader searching for "{keyword}" would want — not generic SEO points.

Return your answer as a JSON array with this structure:
[
  {{
    "gap_title": "Short angle title (max 10 words)",
    "description": "Why this is missing and how to address it (2 sentences)",
    "suggested_heading": "Exact H2 heading to use in the article"
  }}
]

Return ONLY the JSON array, no other text."""

    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are an expert SEO content strategist. Return only valid JSON."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()

    # Extract JSON array from response
    try:
        # Handle potential markdown code blocks
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        gaps = json.loads(raw)
        return gaps
    except json.JSONDecodeError:
        logger.error(f"Could not parse Groq gap analysis JSON: {raw[:200]}")
        return [{"gap_title": "Parsing error", "description": raw[:300], "suggested_heading": ""}]


# ── Main public function ──────────────────────────────────────────────────────
def run(keyword: str, competitor_urls: list[str]) -> list[dict]:
    """
    Perform competitor gap analysis.

    Args:
        keyword         : Target SEO keyword.
        competitor_urls : List of top competitor URLs (usually top 3 from keyword research).

    Returns:
        List of gap dicts, saved to outputs/competitor_gaps.json.
    """
    logger.info(f"▶ Competitor Analysis | keyword='{keyword}' | urls={len(competitor_urls)}")

    # Scrape up to 3 competitor pages
    scraped = []
    for url in competitor_urls[:3]:
        page_data = _scrape_page(url)
        if page_data["headings"]:
            scraped.append(page_data)

    if not scraped:
        logger.warning("No competitor pages could be scraped. Returning empty gaps.")
        return []

    # Analyze with Groq
    gaps = _analyze_gaps_with_groq(keyword, scraped)

    # Build full output
    output = {
        "keyword":          keyword,
        "competitors_analyzed": len(scraped),
        "competitor_urls":  [p["url"] for p in scraped],
        "content_gaps":     gaps,
    }

    output_path = os.path.join(config.OUTPUT_DIR, "competitor_gaps.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Competitor Analysis complete. {len(gaps)} gaps found → {output_path}")
    return gaps


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Competitor Gap Analysis Module")
    parser.add_argument("--keyword", required=True, help="Target keyword")
    parser.add_argument("--urls",    required=True, nargs="+", help="Competitor URLs")
    args = parser.parse_args()
    gaps = run(args.keyword, args.urls)
    print(f"\n{len(gaps)} Content Gaps Found:")
    for gap in gaps:
        print(f"  • {gap.get('gap_title')}: {gap.get('suggested_heading')}")
