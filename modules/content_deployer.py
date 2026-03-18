"""
modules/content_deployer.py — Module 5: Auto-Deploy Content to GitHub
- Converts Markdown → full SEO HTML page
- Pushes to GitHub repository via PyGithub (GitHub REST API)
- Creates/updates file at posts/{slug}.html in the repo
"""

import json
import os
import base64
from datetime import datetime

from github import Github, GithubException

import config
from utils.logger import get_logger
from utils.retry import retry
from utils.html_converter import markdown_to_html, slugify

logger = get_logger(__name__)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)


@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _push_to_github(
    repo_name: str,
    file_path: str,
    html_content: str,
    commit_message: str,
) -> dict:
    """
    Push an HTML file to GitHub repository.
    Creates the file if it doesn't exist; updates it if it does.
    """
    g    = Github(config.GITHUB_TOKEN)
    repo = g.get_repo(repo_name)

    content_bytes = html_content.encode("utf-8")

    try:
        # Check if file already exists (update mode)
        existing = repo.get_contents(file_path)
        result = repo.update_file(
            path=file_path,
            message=commit_message,
            content=content_bytes,
            sha=existing.sha,
        )
        action = "updated"
    except GithubException as e:
        if e.status == 404:
            # File doesn't exist — create it
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content_bytes,
            )
            action = "created"
        else:
            raise

    commit_sha = result["commit"].sha
    # Build GitHub Pages URL (if enabled)
    username, repo_name_only = repo_name.split("/", 1)
    pages_url = f"https://{username}.github.io/{repo_name_only}/{file_path}"

    return {
        "action":      action,
        "file_path":   file_path,
        "commit_sha":  commit_sha,
        "pages_url":   pages_url,
        "repo_url":    f"https://github.com/{repo_name}/blob/main/{file_path}",
    }


# ── Main public function ──────────────────────────────────────────────────────
def run(content_data: dict) -> dict:
    """
    Convert content to HTML and deploy to GitHub.

    Args:
        content_data : Dict from content_generator.run() with keys:
                       keyword, title, meta_description, article_markdown, schema_json_ld.

    Returns:
        Deployment result dict.
    """
    logger.info(f"▶ Content Deployment | repo='{config.GITHUB_REPO}'")

    if not config.GITHUB_TOKEN or not config.GITHUB_REPO:
        logger.warning("GitHub credentials not set — skipping deployment.")
        return {"status": "skipped", "reason": "GITHUB_TOKEN or GITHUB_REPO not set in .env"}

    title       = content_data.get("title", "SEO Article")
    meta_desc   = content_data.get("meta_description", "")
    keyword     = content_data.get("keyword", "")
    markdown    = content_data.get("article_markdown", "")
    schema      = content_data.get("schema_json_ld", "")

    # Convert to HTML
    html_content = markdown_to_html(
        markdown_text=markdown,
        title=title,
        meta_description=meta_desc,
        keyword=keyword,
        schema_json=schema,
    )

    # Build file path
    slug      = slugify(title) or f"post-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    file_path = f"posts/{slug}.html"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f"[AI-SEO] Generated: {title[:60]} | {timestamp}"

    # Save HTML locally too
    local_html_path = os.path.join(config.OUTPUT_DIR, f"{slug}.html")
    with open(local_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Push to GitHub
    deploy_result = _push_to_github(
        repo_name=config.GITHUB_REPO,
        file_path=file_path,
        html_content=html_content,
        commit_message=commit_msg,
    )

    output = {
        "title":         title,
        "slug":          slug,
        "local_html":    local_html_path,
        **deploy_result,
    }

    out_path = os.path.join(config.OUTPUT_DIR, "deployment_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    logger.info(
        f"✅ Deployed ({deploy_result['action']}): {deploy_result['repo_url']}"
    )
    return output


if __name__ == "__main__":
    # Quick test with minimal content
    test_data = {
        "keyword":          "AI marketing tools",
        "title":            "Top AI Marketing Tools in 2024",
        "meta_description": "Discover the best AI tools to automate your marketing.",
        "article_markdown": "# Top AI Marketing Tools in 2024\n\nContent here...\n\n## Why AI Tools Matter\n\nMore content.",
        "schema_json_ld":   "",
    }
    result = run(test_data)
    print(f"\nDeploy result: {result}")
