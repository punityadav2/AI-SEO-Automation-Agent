"""
modules/keyword_research.py — Module 1: Keyword Research
- Queries SerpAPI for search results
- Falls back to Google Custom Search or BeautifulSoup scraping if quota exhausted
- Scores keywords: Score = volume_proxy / difficulty_proxy
- Supports per-platform keyword targeting (website / gmb / linkedin)
"""

import json
import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup

import config
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger(__name__)

os.makedirs(config.OUTPUT_DIR, exist_ok=True)

# ── Platform-specific keyword modifiers ───────────────────────────────────────
PLATFORM_MODIFIERS = {
    "website": [
        "best", "how to", "guide", "tips", "examples", "services", "agency"
    ],
    "gmb": [
        f"near me", f"in {config.TARGET_CITY}",
        f"{config.TARGET_CITY} services", "local", "top rated", "affordable"
    ],
    "linkedin": [
        "how to", "professional guide", "strategy", "trends 2024",
        "best practices", "industry insights"
    ],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


# ── SerpAPI call ──────────────────────────────────────────────────────────────
@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _fetch_serp_results(query: str) -> list[dict]:
    """Call SerpAPI and return list of organic results."""
    if not config.SERPAPI_KEY:
        logger.warning("SERPAPI_KEY not set — falling back to scraper.")
        return _scrape_google_results(query)

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": config.SERPAPI_KEY,
        "num": 10,
        "hl": "en",
        "gl": "in",   # India locale; change as needed
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        logger.warning(f"SerpAPI error: {data['error']} — switching to fallback.")
        return _scrape_google_results(query)

    results = []
    for i, r in enumerate(data.get("organic_results", []), start=1):
        results.append({
            "position": i,
            "title": r.get("title", ""),
            "link": r.get("link", ""),
            "snippet": r.get("snippet", ""),
        })
    return results


def _scrape_google_results(query: str) -> list[dict]:
    """
    Fallback: Scrape Google search page with BeautifulSoup.
    Used when SerpAPI quota is exhausted.
    """
    logger.info(f"Scraping Google for: '{query}'")
    time.sleep(random.uniform(2.0, 5.0))   # polite delay

    search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        results = []
        for i, div in enumerate(soup.select("div.tF2Cxc")[:10], start=1):
            title_el  = div.select_one("h3")
            link_el   = div.select_one("a")
            snippet_el = div.select_one("div.VwiC3b")
            results.append({
                "position": i,
                "title": title_el.get_text() if title_el else "",
                "link": link_el["href"] if link_el else "",
                "snippet": snippet_el.get_text() if snippet_el else "",
            })
        return results
    except Exception as exc:
        logger.error(f"Scraper fallback failed: {exc}")
        return []


# ── Keyword scoring ───────────────────────────────────────────────────────────
def _score_keyword(results: list[dict]) -> float:
    """
    Score = volume_proxy / difficulty_proxy
    volume_proxy   = number of results returned (10 max)
    difficulty_proxy = average position of top results (lower position = harder)
    """
    if not results:
        return 0.0
    volume_proxy = len(results)
    avg_position = sum(r["position"] for r in results) / len(results)
    difficulty_proxy = max(avg_position, 1)
    return round(volume_proxy / difficulty_proxy, 4)


# ── Main public function ──────────────────────────────────────────────────────
def run(seed_keyword: str, platform: str = "website") -> list[dict]:
    """
    Perform keyword research for a given seed keyword and platform.

    Args:
        seed_keyword : The primary keyword entered by the user.
        platform     : Target platform — 'website', 'gmb', or 'linkedin'.

    Returns:
        List of keyword dicts sorted by score (descending), saved to outputs/.
    """
    logger.info(f"▶ Keyword Research | keyword='{seed_keyword}' | platform='{platform}'")
    platform = platform.lower()
    modifiers = PLATFORM_MODIFIERS.get(platform, PLATFORM_MODIFIERS["website"])

    # Build keyword variants
    keyword_variants = [seed_keyword]
    for mod in modifiers:
        keyword_variants.append(f"{seed_keyword} {mod}")

    scored_keywords = []
    for kw in keyword_variants[:8]:   # cap to 8 variants to preserve API quota
        logger.info(f"  Researching: '{kw}'")
        results = _fetch_serp_results(kw)
        score = _score_keyword(results)

        top_url = results[0]["link"] if results else ""
        scored_keywords.append({
            "keyword":     kw,
            "platform":    platform,
            "score":       score,
            "result_count": len(results),
            "top_url":     top_url,
            "difficulty":  "Low" if score > 1.5 else ("Medium" if score > 0.8 else "High"),
        })

        time.sleep(random.uniform(config.DELAY_MIN_SECS, config.DELAY_MAX_SECS))

    # Sort by score descending
    scored_keywords.sort(key=lambda x: x["score"], reverse=True)

    # Filter out very low-scoring keywords
    scored_keywords = [k for k in scored_keywords if k["score"] >= config.MIN_KEYWORD_SCORE]

    # Save output
    output_path = os.path.join(config.OUTPUT_DIR, "keyword_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scored_keywords, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Keyword Research complete. {len(scored_keywords)} keywords saved → {output_path}")
    return scored_keywords


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Keyword Research Module")
    parser.add_argument("--keyword",  required=True, help="Seed keyword")
    parser.add_argument("--platform", default="website", help="website | gmb | linkedin")
    args = parser.parse_args()
    results = run(args.keyword, args.platform)
    print(f"\nTop Keywords:\n")
    for kw in results[:config.TOP_KEYWORDS_TO_USE]:
        print(f"  [{kw['difficulty']}] {kw['keyword']} — Score: {kw['score']}")
