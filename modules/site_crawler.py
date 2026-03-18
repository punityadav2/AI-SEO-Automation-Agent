"""
modules/site_crawler.py — Module 4a: Screaming Frog Alternative
- BFS site crawler using requests + BeautifulSoup
- Checks: broken links, missing meta, thin content, duplicate titles, image alt text
- Outputs crawl_report.json
"""

import json
import os
import time
import random
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import config
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger(__name__)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SEOCrawlerBot/1.0; +https://github.com/seo-agent)"
    )
}
MAX_PAGES_TO_CRAWL = 50   # cap to avoid excessive requests


def _is_same_domain(base_url: str, url: str) -> bool:
    return urlparse(base_url).netloc == urlparse(url).netloc


@retry(max_attempts=2, backoff=1.5)
def _fetch_url(url: str) -> tuple[int, str]:
    """Fetch a URL, return (status_code, html_text)."""
    resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
    return resp.status_code, resp.text


def _extract_page_data(url: str, status_code: int, html: str, keyword: str = "") -> dict:
    """Extract SEO-relevant data from a page."""
    soup = BeautifulSoup(html, "lxml")

    title_el    = soup.find("title")
    meta_el     = soup.find("meta", attrs={"name": "description"})
    h1_list     = [h.get_text(strip=True) for h in soup.find_all("h1")]
    body_text   = soup.get_text(separator=" ", strip=True)
    word_count  = len(body_text.split())

    # Image alt check
    images       = soup.find_all("img")
    missing_alt  = sum(1 for img in images if not img.get("alt"))

    # Keyword density
    kw_density = 0.0
    if keyword and word_count > 0:
        kw_count   = body_text.lower().count(keyword.lower())
        kw_density = round(kw_count / word_count, 4)

    # Extract all links on page
    links = []
    for a in soup.find_all("a", href=True):
        links.append(urljoin(url, a["href"]))

    issues = []
    if not title_el:
        issues.append("MISSING_TITLE")
    elif len(title_el.get_text()) > config.META_TITLE_MAX:
        issues.append(f"TITLE_TOO_LONG ({len(title_el.get_text())} chars)")

    if not meta_el or not meta_el.get("content"):
        issues.append("MISSING_META_DESC")
    elif len(meta_el["content"]) > config.META_DESC_MAX:
        issues.append(f"META_DESC_TOO_LONG ({len(meta_el['content'])} chars)")

    if len(h1_list) == 0:
        issues.append("MISSING_H1")
    elif len(h1_list) > 1:
        issues.append(f"MULTIPLE_H1 ({len(h1_list)})")

    if word_count < config.MIN_CONTENT_WORDS:
        issues.append(f"THIN_CONTENT ({word_count} words < {config.MIN_CONTENT_WORDS})")

    if missing_alt > 0:
        issues.append(f"MISSING_ALT_TEXT ({missing_alt} images)")

    if keyword and kw_density < config.IDEAL_KEYWORD_DENSITY_MIN:
        issues.append(f"LOW_KEYWORD_DENSITY ({kw_density:.2%})")
    elif keyword and kw_density > config.IDEAL_KEYWORD_DENSITY_MAX:
        issues.append(f"KEYWORD_STUFFING ({kw_density:.2%})")

    return {
        "url":         url,
        "status_code": status_code,
        "title":       title_el.get_text(strip=True) if title_el else "",
        "meta_desc":   meta_el["content"] if meta_el and meta_el.get("content") else "",
        "h1_count":    len(h1_list),
        "word_count":  word_count,
        "kw_density":  kw_density,
        "missing_alt": missing_alt,
        "issues":      issues,
        "links":       links,
    }


# ── Main public function ──────────────────────────────────────────────────────
def run(start_url: str, keyword: str = "") -> dict:
    """
    Crawl a website and return a full SEO crawl report.

    Args:
        start_url : Root URL to crawl.
        keyword   : Primary keyword for density check.

    Returns:
        Crawl report dict, saved to outputs/crawl_report.json.
    """
    logger.info(f"▶ Site Crawler | start='{start_url}' | keyword='{keyword}'")

    visited   = set()
    queue     = deque([start_url])
    pages     = []
    broken    = []

    while queue and len(visited) < MAX_PAGES_TO_CRAWL:
        url = queue.popleft()

        # Skip already visited, non-http, and off-domain URLs
        if url in visited:
            continue
        if not url.startswith("http"):
            continue
        if not _is_same_domain(start_url, url):
            continue

        visited.add(url)
        logger.info(f"  Crawling ({len(visited)}/{MAX_PAGES_TO_CRAWL}): {url}")
        time.sleep(random.uniform(0.5, 1.5))   # polite crawl delay

        try:
            status, html = _fetch_url(url)
        except Exception as exc:
            logger.warning(f"  Fetch error for {url}: {exc}")
            broken.append({"url": url, "error": str(exc)})
            continue

        if status >= 400:
            broken.append({"url": url, "status": status})
            logger.warning(f"  Broken link: {url} → {status}")
            continue

        if "text/html" not in html[:100]:   # rough check
            continue

        page_data = _extract_page_data(url, status, html, keyword)
        pages.append(page_data)

        # Add new links to queue
        for link in page_data.pop("links", []):
            if link not in visited and _is_same_domain(start_url, link):
                queue.append(link)

    # Aggregate stats
    all_titles     = [p["title"] for p in pages if p["title"]]
    duplicate_titles = len(all_titles) - len(set(all_titles))
    pages_with_issues = [p for p in pages if p["issues"]]

    summary = {
        "start_url":       start_url,
        "pages_crawled":   len(pages),
        "broken_links":    len(broken),
        "duplicate_titles": duplicate_titles,
        "pages_with_issues": len(pages_with_issues),
        "avg_word_count":  round(sum(p["word_count"] for p in pages) / max(len(pages), 1)),
    }

    report = {
        "summary":      summary,
        "broken_links": broken,
        "pages":        pages,
    }

    out_path = os.path.join(config.OUTPUT_DIR, "crawl_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(
        f"✅ Crawl complete: {len(pages)} pages, {len(broken)} broken, "
        f"{len(pages_with_issues)} issues → {out_path}"
    )
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",     required=True)
    parser.add_argument("--keyword", default="")
    args = parser.parse_args()
    report = run(args.url, args.keyword)
    print(f"\nCrawl Summary: {report['summary']}")
