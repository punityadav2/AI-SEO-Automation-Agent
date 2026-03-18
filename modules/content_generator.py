"""
modules/content_generator.py — Module 3a: Website SEO Content Generator
- Generates full SEO-optimised articles using Groq API (llama3-8b-8192)
- Uses competitor gaps to produce unique, non-generic content
- Outputs: article markdown, JSON-LD schema, meta tags
"""

import json
import os
import re
import time
import random
from groq import Groq

import config
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger(__name__)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)


@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _call_groq(messages: list, max_tokens: int = 2048) -> str:
    """Generic Groq API call with retry."""
    client = Groq(api_key=config.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=messages,
        temperature=0.75,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def _generate_meta(keyword: str, gaps: list[dict]) -> dict:
    """Generate SEO title and meta description."""
    gap_angles = "\n".join(
        f"- {g.get('gap_title', '')}" for g in gaps[:3]
    ) if gaps else "No specific gaps provided."

    prompt = f"""Generate an SEO title and meta description for a web page targeting "{keyword}".

Content angles to cover (unique selling points vs competitors):
{gap_angles}

Requirements:
- Title: 55-60 characters, keyword-first, compelling
- Meta description: 145-155 characters, includes keyword + clear CTA

Return ONLY JSON:
{{"title": "...", "meta_description": "..."}}"""

    raw = _call_groq([
        {"role": "system", "content": "You are an SEO expert. Return only valid JSON."},
        {"role": "user",   "content": prompt},
    ], max_tokens=300)

    try:
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception:
        logger.warning("Meta JSON parse failed — using defaults.")
        return {
            "title": f"{keyword.title()} — Complete Guide",
            "meta_description": f"Learn everything about {keyword}. Expert tips, strategies and actionable insights.",
        }


def _generate_article(keyword: str, meta: dict, gaps: list[dict]) -> str:
    """Generate a full 1000+ word SEO article in Markdown."""
    gap_headings = "\n".join(
        f"- {g.get('suggested_heading', g.get('gap_title', ''))}" for g in gaps
    ) if gaps else ""

    prompt = f"""Write a high-quality, SEO-optimised article for the keyword: "{keyword}".

Article title: {meta['title']}
Target keyword density: 1-2% (natural placement only, no keyword stuffing)
Minimum length: 1000 words

You MUST include these unique content sections (these are gaps competitors MISSED):
{gap_headings}

Structure:
1. H1: Use the article title
2. 3-4 H2 sections with H3 subsections
3. A practical FAQ section (5 questions)
4. A clear conclusion with CTA

Rules:
- Write informatively, not generically
- No filler phrases like "In today's world" or "In conclusion, it is clear"
- Use real examples, data points, or step-by-step advice
- Format as clean Markdown"""

    return _call_groq([
        {"role": "system", "content": "You are a senior SEO content writer. Write in a professional, engaging tone."},
        {"role": "user",   "content": prompt},
    ], max_tokens=2048)


def _generate_schema(keyword: str, title: str, meta_desc: str) -> str:
    """Generate JSON-LD Article schema markup."""
    import datetime
    today = datetime.date.today().isoformat()
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": meta_desc,
        "keywords": keyword,
        "datePublished": today,
        "dateModified": today,
        "author": {
            "@type": "Organization",
            "name": config.TARGET_INDUSTRY.title()
        },
        "publisher": {
            "@type": "Organization",
            "name": config.TARGET_INDUSTRY.title()
        }
    }

    # Also add FAQ schema if article likely has FAQ section
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"What is {keyword}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"See our comprehensive guide on {keyword} above."
                }
            }
        ]
    }
    return json.dumps([schema, faq_schema], indent=2)


# ── Main public function ──────────────────────────────────────────────────────
def run(keyword: str, gaps: list[dict]) -> dict:
    """
    Generate SEO-optimised website content.

    Args:
        keyword : Primary target keyword.
        gaps    : Content gaps from competitor_analysis module.

    Returns:
        Dict with title, meta_description, article_markdown, schema, saved to outputs/.
    """
    logger.info(f"▶ Website Content Generation | keyword='{keyword}'")

    meta    = _generate_meta(keyword, gaps)
    logger.info(f"  Title: {meta['title']}")

    article = _generate_article(keyword, meta, gaps)
    schema  = _generate_schema(keyword, meta["title"], meta["meta_description"])

    output = {
        "keyword":          keyword,
        "title":            meta["title"],
        "meta_description": meta["meta_description"],
        "article_markdown": article,
        "schema_json_ld":   schema,
        "word_count":       len(article.split()),
    }

    # Save markdown
    md_path = os.path.join(config.OUTPUT_DIR, "website_content.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {meta['title']}\n\n")
        f.write(f"**Meta:** {meta['meta_description']}\n\n---\n\n")
        f.write(article)

    # Save JSON
    json_path = os.path.join(config.OUTPUT_DIR, "website_content.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Content generated ({output['word_count']} words) → {md_path}")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    args = parser.parse_args()
    result = run(args.keyword, [])
    print(f"\nGenerated: {result['title']} ({result['word_count']} words)")
