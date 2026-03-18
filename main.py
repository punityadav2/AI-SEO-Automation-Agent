"""
main.py — AI SEO Automation Agent: Master Pipeline Runner
Orchestrates all modules end-to-end:
  M1 Keyword Research → M2 Competitor Analysis → M3 Content Generation (Website + GMB + LinkedIn)
  → M4 Site Crawl + SEO Audit → M5 Content Deployment → M6 Reporting
"""

import os
import sys
import json
import argparse
from datetime import datetime

import config
from utils.logger import get_logger

logger = get_logger("main")


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║          AI SEO AUTOMATION AGENT  🤖                     ║
║  Keyword → Content → Deploy → Report (All Free Tools)    ║
╚══════════════════════════════════════════════════════════╝
""")


def print_step(step: int, title: str):
    print(f"\n{'─'*60}")
    print(f"  STEP {step}: {title}")
    print(f"{'─'*60}")


def run_pipeline(keyword: str, platform: str, site_url: str = ""):
    """
    Run the complete SEO automation pipeline.

    Args:
        keyword  : Seed keyword (e.g. "AI marketing tools")
        platform : Target platform — 'website', 'gmb', or 'linkedin'
        site_url : Your website URL for site crawl + GSC lookup (optional)
    """
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.LOG_DIR, exist_ok=True)
    start_time = datetime.now()

    print_banner()
    logger.info(f"Pipeline started | keyword='{keyword}' | platform='{platform}'")

    # ── STEP 1: Keyword Research ──────────────────────────────────────────────
    print_step(1, "Keyword Research")
    from modules.keyword_research import run as keyword_run
    keywords = keyword_run(seed_keyword=keyword, platform=platform)
    top_keywords = keywords[:config.TOP_KEYWORDS_TO_USE]

    if not top_keywords:
        logger.error("Keyword research returned no results. Check API key or fallback scraper.")
        sys.exit(1)

    primary_kw = top_keywords[0]["keyword"]
    competitor_urls = [k["top_url"] for k in top_keywords if k.get("top_url")][:3]

    print(f"  ✅ Top keyword: '{primary_kw}'")
    print(f"  📋 {len(top_keywords)} keywords scored and saved")

    # ── STEP 2: Competitor Analysis ───────────────────────────────────────────
    print_step(2, "Competitor Gap Analysis")
    from modules.competitor_analysis import run as competitor_run
    gaps = competitor_run(keyword=primary_kw, competitor_urls=competitor_urls)
    print(f"  ✅ {len(gaps)} content gaps identified")
    for gap in gaps[:3]:
        print(f"     💡 {gap.get('gap_title', '')}")

    # ── STEP 3a: Website Content Generation ───────────────────────────────────
    print_step(3, "AI Content Generation — Website")
    from modules.content_generator import run as content_run
    website_content = content_run(keyword=primary_kw, gaps=gaps)
    print(f"  ✅ Article: '{website_content['title']}' ({website_content['word_count']} words)")

    # ── STEP 3b: GMB Content (runs regardless of selected platform) ───────────
    print_step(4, "AI Content Generation — Google My Business")
    from modules.gmb_content_generator import run as gmb_run
    gmb_result = gmb_run(keyword=primary_kw)
    gmb_status = gmb_result.get("publish_result", {}).get("status", "unknown")
    print(f"  ✅ GMB post generated | Status: {gmb_status}")

    # ── STEP 3c: LinkedIn Content ─────────────────────────────────────────────
    print_step(5, "AI Content Generation — LinkedIn")
    from modules.linkedin_content_generator import run as linkedin_run
    linkedin_result = linkedin_run(keyword=primary_kw, gaps=gaps)
    print(f"  ✅ LinkedIn post generated")

    # ── STEP 4a: Site Crawl (if site URL provided) ────────────────────────────
    crawl_report = {}
    if site_url:
        print_step(6, f"Site Crawl + SEO Audit — {site_url}")
        from modules.site_crawler import run as crawler_run
        crawl_report = crawler_run(start_url=site_url, keyword=primary_kw)
        s = crawl_report.get("summary", {})
        print(f"  ✅ Crawled {s.get('pages_crawled', 0)} pages | "
              f"{s.get('broken_links', 0)} broken | "
              f"{s.get('pages_with_issues', 0)} with issues")
    else:
        print(f"\n  ── Skipping site crawl (no --site-url provided) ──")

    # ── STEP 4b: SEO Audit on generated content ───────────────────────────────
    print_step(7, "On-Page SEO Audit — Generated Content")
    from modules.seo_audit import run as audit_run
    audit = audit_run(
        content=website_content["article_markdown"],
        keyword=primary_kw,
        title=website_content["title"],
        meta_description=website_content["meta_description"],
    )
    print(f"  ✅ SEO Score: {audit['seo_score']}/100 (Grade {audit['grade']})")
    print(f"  {audit['summary']}")
    if audit.get("improvements"):
        print("  🔧 Improvements needed:")
        for imp in audit["improvements"]:
            print(f"     • {imp}")

    # ── STEP 5: Content Deployment ────────────────────────────────────────────
    print_step(8, "Content Deployment → GitHub")
    from modules.content_deployer import run as deploy_run
    deploy_result = deploy_run(content_data=website_content)
    github_url = deploy_result.get("repo_url", "")
    print(f"  ✅ Deploy status: {deploy_result.get('action', 'skipped')}")
    if github_url:
        print(f"  🔗 GitHub: {github_url}")

    # ── STEP 6: Reporting ─────────────────────────────────────────────────────
    print_step(9, "Weekly Rank Report → GSC + Google Sheets")
    from modules.reporter import run as report_run
    report = report_run(
        keyword=primary_kw,
        platform=platform,
        content_title=website_content["title"],
        audit_score=audit["seo_score"],
        github_url=github_url,
        gmb_status=gmb_status,
    )
    gsc = report.get("gsc_data", {})
    print(f"  ✅ Source: {gsc.get('data_source', 'N/A')}")
    print(f"  Position: {gsc.get('position', 'N/A')} | "
          f"CTR: {gsc.get('ctr', 'N/A')}% | "
          f"Impressions: {gsc.get('impressions', 'N/A')}")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start_time).seconds
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                  PIPELINE COMPLETE ✅                    ║
╠══════════════════════════════════════════════════════════╣
║  Keyword:     {primary_kw[:44]:<44}  ║
║  SEO Score:   {audit['seo_score']}/100 (Grade {audit['grade']})                          ║
║  GMB Status:  {gmb_status:<44}  ║
║  Time taken:  {elapsed}s                                             ║
╠══════════════════════════════════════════════════════════╣
║  Outputs saved to: outputs/                              ║
║  Logs saved to:    logs/                                 ║
╚══════════════════════════════════════════════════════════╝
""")

    logger.info(f"Pipeline complete in {elapsed}s | Score: {audit['seo_score']}/100")
    return {
        "keyword":         primary_kw,
        "keywords":        top_keywords,
        "gaps":            gaps,
        "website_content": website_content,
        "gmb_result":      gmb_result,
        "linkedin_result": linkedin_result,
        "crawl_report":    crawl_report,
        "audit":           audit,
        "deploy_result":   deploy_result,
        "rank_report":     report,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI SEO Automation Agent — Full Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --keyword "digital marketing agency" --platform website
  python main.py --keyword "plumber in Mumbai" --platform gmb --site-url https://example.com
  python main.py --keyword "LinkedIn growth strategy" --platform linkedin
        """
    )
    parser.add_argument("--keyword",   required=True,  help="Seed keyword to target")
    parser.add_argument("--platform",  default="website", choices=["website", "gmb", "linkedin"],
                        help="Target platform (default: website)")
    parser.add_argument("--site-url",  default="",     help="Your website URL for site crawl + GSC data")

    args = parser.parse_args()
    run_pipeline(
        keyword=args.keyword,
        platform=args.platform,
        site_url=args.site_url,
    )
