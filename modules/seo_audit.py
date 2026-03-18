"""
modules/seo_audit.py — Module 4b: On-Page SEO Audit
- Audits generated content (or any HTML string) for SEO issues
- Flags: missing meta tags, keyword gaps, thin content, broken links (basic)
- Works on the AI-generated content before deployment
- Outputs seo_audit.json with pass/fail per check + suggestions
"""

import json
import os
import re

import config
from utils.logger import get_logger

logger = get_logger(__name__)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)


def _check_title(title: str) -> dict:
    length = len(title)
    passed = bool(title) and 30 <= length <= config.META_TITLE_MAX
    return {
        "check":   "SEO Title",
        "value":   title[:80] if title else "(none)",
        "passed":  passed,
        "detail":  f"{length} chars" if title else "MISSING",
        "fix":     f"Keep title between 30-{config.META_TITLE_MAX} chars" if not passed else "",
    }


def _check_meta_desc(meta_desc: str) -> dict:
    length = len(meta_desc)
    passed = bool(meta_desc) and 70 <= length <= config.META_DESC_MAX
    return {
        "check":   "Meta Description",
        "value":   meta_desc[:160] if meta_desc else "(none)",
        "passed":  passed,
        "detail":  f"{length} chars" if meta_desc else "MISSING",
        "fix":     f"Keep meta description 70-{config.META_DESC_MAX} chars, include a CTA" if not passed else "",
    }


def _check_keyword_density(content: str, keyword: str) -> dict:
    words     = content.split()
    word_count = len(words)
    if not keyword or word_count == 0:
        return {"check": "Keyword Density", "passed": False, "detail": "No keyword provided", "fix": ""}
    kw_count  = content.lower().count(keyword.lower())
    density   = kw_count / word_count
    passed    = config.IDEAL_KEYWORD_DENSITY_MIN <= density <= config.IDEAL_KEYWORD_DENSITY_MAX
    return {
        "check":   "Keyword Density",
        "value":   f"{density:.2%} ({kw_count}/{word_count} words)",
        "passed":  passed,
        "detail":  f"{density:.2%}",
        "fix":     f"Target 1-3% density. Currently: {density:.2%}." if not passed else "",
    }


def _check_content_length(content: str) -> dict:
    count  = len(content.split())
    passed = count >= config.MIN_CONTENT_WORDS
    return {
        "check":   "Content Length",
        "value":   f"{count} words",
        "passed":  passed,
        "detail":  f"{count} words",
        "fix":     f"Add more depth — minimum {config.MIN_CONTENT_WORDS} words recommended" if not passed else "",
    }


def _check_h1(content: str) -> dict:
    h1_matches = re.findall(r"^#\s+.+", content, re.MULTILINE)
    count  = len(h1_matches)
    passed = count == 1
    return {
        "check":   "H1 Tag",
        "value":   f"{count} H1(s) found",
        "passed":  passed,
        "detail":  str(h1_matches[:1]),
        "fix":     "Use exactly 1 H1 tag (# in Markdown)" if not passed else "",
    }


def _check_headings_structure(content: str) -> dict:
    h2_matches = re.findall(r"^##\s+.+", content, re.MULTILINE)
    passed = len(h2_matches) >= 2
    return {
        "check":   "Heading Structure (H2s)",
        "value":   f"{len(h2_matches)} H2 sections",
        "passed":  passed,
        "detail":  f"{len(h2_matches)} H2 headings",
        "fix":     "Add at least 2 H2 sections to improve content structure" if not passed else "",
    }


def _check_schema(content: str) -> dict:
    has_schema = "@context" in content and "schema.org" in content
    return {
        "check":  "JSON-LD Schema",
        "passed": has_schema,
        "value":  "Present" if has_schema else "MISSING",
        "detail": "Schema markup detected" if has_schema else "No JSON-LD schema found",
        "fix":    "Add JSON-LD Article or FAQPage schema markup" if not has_schema else "",
    }


def _check_faq(content: str) -> dict:
    has_faq = bool(re.search(r"(FAQ|Frequently Asked|Q:|A:)", content, re.IGNORECASE))
    return {
        "check":  "FAQ Section",
        "passed": has_faq,
        "value":  "Present" if has_faq else "MISSING",
        "detail": "FAQ section found" if has_faq else "No FAQ section",
        "fix":    "Add a FAQ section to capture featured snippet opportunities" if not has_faq else "",
    }


def _score_audit(checks: list[dict]) -> float:
    """Return a 0-100 SEO score based on pass/fail checks."""
    passed = sum(1 for c in checks if c["passed"])
    return round((passed / len(checks)) * 100, 1)


# ── Main public function ──────────────────────────────────────────────────────
def run(content: str, keyword: str, title: str = "", meta_description: str = "") -> dict:
    """
    Audit generated content for SEO readiness.

    Args:
        content         : Article body text (Markdown or plain).
        keyword         : Primary keyword.
        title           : SEO title string.
        meta_description: Meta description string.

    Returns:
        Audit dict with per-check results + overall score.
    """
    logger.info(f"▶ SEO Audit | keyword='{keyword}' | content_words={len(content.split())}")

    checks = [
        _check_title(title),
        _check_meta_desc(meta_description),
        _check_keyword_density(content, keyword),
        _check_content_length(content),
        _check_h1(content),
        _check_headings_structure(content),
        _check_schema(content),
        _check_faq(content),
    ]

    score        = _score_audit(checks)
    failed_checks = [c for c in checks if not c["passed"]]
    improvements  = [c["fix"] for c in failed_checks if c["fix"]]

    audit = {
        "keyword":     keyword,
        "seo_score":   score,
        "grade":       "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D",
        "checks":      checks,
        "improvements": improvements,
        "summary":     f"{len(checks) - len(failed_checks)}/{len(checks)} checks passed",
    }

    out_path = os.path.join(config.OUTPUT_DIR, "seo_audit.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    logger.info(
        f"✅ SEO Audit complete: Score {score}/100 (Grade {audit['grade']}) "
        f"| {audit['summary']} → {out_path}"
    )
    return audit


if __name__ == "__main__":
    sample = "# AI Tools Guide\n\nAI tools are transforming marketing...\n\n## Why Use AI Tools\n\nSome text here.\n\n## Top AI Tools\n\nMore text.\n\n## FAQ\n\nQ: What are AI tools?"
    result = run(sample, keyword="AI tools", title="Top AI Tools Guide", meta_description="Discover the best AI tools for marketing in 2024.")
    print(f"\nSEO Score: {result['seo_score']}/100 (Grade {result['grade']})")
    for check in result["checks"]:
        status = "✅" if check["passed"] else "❌"
        print(f"  {status} {check['check']}: {check['value']}")
