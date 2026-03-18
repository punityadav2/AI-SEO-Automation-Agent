"""
utils/html_converter.py — Convert Markdown content to clean HTML with SEO meta tags
"""

import markdown as md_lib
import re


def markdown_to_html(
    markdown_text: str,
    title: str = "",
    meta_description: str = "",
    keyword: str = "",
    schema_json: str = "",
) -> str:
    """
    Convert Markdown to a full HTML page with SEO meta tags and optional JSON-LD schema.

    Args:
        markdown_text   : The raw Markdown content.
        title           : SEO title for <title> and og:title.
        meta_description: Meta description string.
        keyword         : Primary keyword for meta keywords tag.
        schema_json     : JSON-LD schema markup string (Article, FAQ, etc.).

    Returns:
        str: Full HTML document as string.
    """
    # Convert markdown → HTML body
    extensions = ["extra", "tables", "toc"]
    html_body = md_lib.markdown(markdown_text, extensions=extensions)

    schema_block = ""
    if schema_json:
        schema_block = f'<script type="application/ld+json">\n{schema_json}\n</script>'

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{meta_description}">
  <meta name="keywords" content="{keyword}">
  <!-- Open Graph -->
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{meta_description}">
  <meta property="og:type" content="article">
  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{meta_description}">
  {schema_block}
</head>
<body>
{html_body}
</body>
</html>"""

    return html_page


def slugify(text: str) -> str:
    """Convert a title string to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    return text
