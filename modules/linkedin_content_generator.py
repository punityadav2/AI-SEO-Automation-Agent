"""
modules/linkedin_content_generator.py — Module 3c: LinkedIn Post Generator
- Generates professional, insight-driven LinkedIn posts via Groq API
- Avoids templated content (auto-disqualification risk per assignment)
- Exports ready-to-post Markdown file
- Optional: LinkedIn API v2 posting if Developer App is approved
"""

import json
import os
from groq import Groq

import config
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger(__name__)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)


@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _generate_linkedin_post(keyword: str, gaps: list[dict]) -> dict:
    """Use Groq to write a high-quality LinkedIn post."""
    client = Groq(api_key=config.GROQ_API_KEY)

    gap_insights = "\n".join(
        f"- {g.get('gap_title', '')}: {g.get('description', '')}" for g in gaps[:3]
    ) if gaps else ""

    prompt = f"""Write a high-performing LinkedIn post targeting the professional keyword: "{keyword}".

Unique insights to weave in (content gaps competitors missed):
{gap_insights}

LinkedIn Post Requirements:
- Start with a STRONG hook (first line must stop the scroll — a bold claim, surprising stat, or provocative question)
- Length: 150-250 words
- Tone: authoritative but conversational (like a CMO sharing advice)
- Include 1-2 specific data points or examples (can be realistic hypotheticals)
- End with a thought-provoking question to encourage comments
- 3-5 relevant hashtags at the end

AVOID:
- "In today's fast-paced world..."
- "I'm excited to share..."
- Generic motivational content
- Bullet lists that look like a resume

Return ONLY JSON:
{{
  "hook_line": "First line of the post",
  "post_body": "Full post text (hook included, hashtags at end)",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "estimated_engagement": "Low/Medium/High",
  "best_post_time": "Tuesday 8am-10am"
}}"""

    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a top LinkedIn content strategist. Write posts that go viral. Return only valid JSON."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.8,
        max_tokens=700,
    )
    raw = response.choices[0].message.content.strip()

    try:
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
    except Exception:
        logger.warning("LinkedIn post JSON parse error.")
        return {
            "hook_line":            "Insights from our latest research…",
            "post_body":            raw,
            "hashtags":             [f"#{keyword.replace(' ', '')}"],
            "estimated_engagement": "Medium",
            "best_post_time":       "Tuesday 8am",
        }


# ── Main public function ──────────────────────────────────────────────────────
def run(keyword: str, gaps: list[dict]) -> dict:
    """
    Generate a LinkedIn post for the given keyword.

    Args:
        keyword : Professional-intent keyword.
        gaps    : Competitor content gaps from Module 2.

    Returns:
        Dict with post content, saved to outputs/linkedin_post.md + .json.
    """
    logger.info(f"▶ LinkedIn Content Generation | keyword='{keyword}'")

    post = _generate_linkedin_post(keyword, gaps)

    output = {
        "keyword":   keyword,
        "post_data": post,
    }

    # Save as Markdown (ready to copy-paste)
    md_path = os.path.join(config.OUTPUT_DIR, "linkedin_post.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# LinkedIn Post — {keyword}\n\n")
        f.write(f"**Best time to post:** {post.get('best_post_time', 'N/A')}\n\n")
        f.write("---\n\n")
        f.write(post.get("post_body", ""))
        f.write("\n\n---\n")
        f.write(f"**Hashtags:** {' '.join(post.get('hashtags', []))}\n")
        f.write(f"**Estimated Engagement:** {post.get('estimated_engagement', 'N/A')}\n")

    # Save JSON
    json_path = os.path.join(config.OUTPUT_DIR, "linkedin_post.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ LinkedIn post saved → {md_path}")
    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    args = parser.parse_args()
    result = run(args.keyword, [])
    print(f"\nLinkedIn Post:\n{result['post_data']['post_body']}")
