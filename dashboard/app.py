# -*- coding: utf-8 -*-
import sys
import json
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI SEO Agent Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

OUTPUT_DIR = "outputs"


def load_json(filename: str) -> dict | list | None:
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252b3b);
        border: 1px solid #2d3348;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .status-pass { color: #00cc88; font-weight: bold; }
    .status-fail { color: #ff4b6b; font-weight: bold; }
    .section-header {
        background: linear-gradient(90deg, #4f46e5, #7c3aed);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 1rem 0 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.shields.io/badge/AI_SEO_Agent-v1.0-blueviolet?style=for-the-badge")
    st.markdown("---")
    st.markdown("### 🔄 Run Pipeline")
    kw_input      = st.text_input("Seed Keyword", placeholder="e.g. digital marketing")
    platform_sel  = st.selectbox("Platform", ["website", "gmb", "linkedin"])
    site_url_inp  = st.text_input("Site URL (optional)", placeholder="https://yoursite.com")

    if st.button("🚀 Run Full Pipeline", type="primary"):
        import subprocess
        
        # Ensure we run from the project root where main.py lives
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        cmd = [sys.executable, "main.py", "--keyword", kw_input, "--platform", platform_sel]
        if site_url_inp:
            cmd += ["--site-url", site_url_inp]
        with st.spinner("Running pipeline... this may take 30-60 seconds"):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    encoding="utf-8",
                    errors="replace",
                    env={**os.environ, "PYTHONUTF8": "1"},
                )
                if result.returncode == 0:
                    st.success("Pipeline completed!")
                else:
                    st.error(f"Pipeline error:\n{result.stderr[-500:]}")
            except Exception as e:
                st.error(f"Error: {e}")
        st.rerun()

    st.markdown("---")
    if st.button("🔃 Refresh Dashboard"):
        st.rerun()

    st.markdown(f"*Last refresh: {datetime.now().strftime('%H:%M:%S')}*")

# ── Main page ─────────────────────────────────────────────────────────────────
st.title("🤖 AI SEO Automation Agent")
st.markdown("Real-time SEO pipeline monitoring — keyword research, content, audit, and rankings")

# ── API Key Warnings ──────────────────────────────────────────────────────────
missing_keys = []
if not os.getenv("GROQ_API_KEY") or (os.getenv("GROQ_API_KEY") or "").startswith("gsk_your_groq_api_key"): missing_keys.append("Groq API Key (GROQ_API_KEY)")
if not os.getenv("SERPAPI_KEY") or (os.getenv("SERPAPI_KEY") or "").startswith("your_serpapi_key"): missing_keys.append("SerpAPI Key (SERPAPI_KEY)")

if missing_keys:
    st.warning("⚠️ **Missing Configuration:** Please set your keys in the `.env` file to run the pipeline.")
    for k in missing_keys: st.markdown(f"- ❌ Missing {k}")
    st.markdown("Dashboard is currently showing **Sample / Dummy Data**.")
else:
    st.success("✅ Core API keys configured.")
st.markdown("---")

# ── Top Metrics Row ───────────────────────────────────────────────────────────
rank_report    = load_json("rank_report.json")
audit_data     = load_json("seo_audit.json")
kw_data        = load_json("keyword_report.json")
deploy_data    = load_json("deployment_result.json")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    kw_count = len(kw_data) if isinstance(kw_data, list) else 0
    st.metric("📋 Keywords Found", kw_count)

with col2:
    score = audit_data.get("seo_score", "—") if audit_data else "—"
    grade = audit_data.get("grade", "") if audit_data else ""
    st.metric("🎯 SEO Score", f"{score}/100", delta=f"Grade {grade}" if grade else None)

with col3:
    pos = rank_report.get("gsc_data", {}).get("position") if rank_report else None
    st.metric("📍 GSC Position", pos if pos else "N/A")

with col4:
    ctr = rank_report.get("gsc_data", {}).get("ctr") if rank_report else None
    st.metric("📊 CTR", f"{ctr}%" if ctr else "N/A")

with col5:
    imp = rank_report.get("gsc_data", {}).get("impressions") if rank_report else None
    st.metric("👁️ Impressions", imp if imp else "N/A")

st.markdown("---")

# ── Row 2: Keyword Table + Audit Results ─────────────────────────────────────
col_kw, col_audit = st.columns([3, 2])

with col_kw:
    st.markdown('<div class="section-header">📋 Keyword Research Results</div>', unsafe_allow_html=True)
    if kw_data and isinstance(kw_data, list):
        df = pd.DataFrame(kw_data)[["keyword", "platform", "score", "difficulty", "result_count"]]
        df.columns = ["Keyword", "Platform", "Score", "Difficulty", "Results"]
        df = df.sort_values("Score", ascending=False)

        def color_difficulty(val):
            colors = {"Low": "background-color: #00cc8833", "Medium": "background-color: #ffaa0033", "High": "background-color: #ff4b6b33"}
            return colors.get(val, "")

        st.dataframe(
            df.style.map(color_difficulty, subset=["Difficulty"]),
            use_container_width=True,
            height=300,
        )
    else:
        st.info("No keyword data yet. Run the pipeline first.")

with col_audit:
    st.markdown('<div class="section-header">✅ SEO Audit Results</div>', unsafe_allow_html=True)
    if audit_data:
        for check in audit_data.get("checks", []):
            icon = "✅" if check["passed"] else "❌"
            st.markdown(f"{icon} **{check['check']}** — `{check.get('value', '')}`")

        st.progress(int(audit_data.get("seo_score", 0)) / 100)
        st.caption(f"Overall: {audit_data.get('summary', '')}")

        if audit_data.get("improvements"):
            with st.expander("🔧 Improvement Suggestions"):
                for imp in audit_data["improvements"]:
                    st.markdown(f"• {imp}")
    else:
        st.info("No audit data yet.")

# ── Row 3: Generated Content Preview ─────────────────────────────────────────
st.markdown('<div class="section-header">📝 Generated Content Preview</div>', unsafe_allow_html=True)

tab_web, tab_gmb, tab_li = st.tabs(["🌐 Website Article", "📍 GMB Post", "💼 LinkedIn Post"])

with tab_web:
    content_path = os.path.join(OUTPUT_DIR, "website_content.md")
    if os.path.exists(content_path):
        with open(content_path, encoding="utf-8") as f:
            content_md = f.read()
        word_count = len(content_md.split())
        st.caption(f"Word count: {word_count}")
        st.markdown(content_md[:3000] + ("..." if len(content_md) > 3000 else ""))
    else:
        st.info("No website content generated yet.")

with tab_gmb:
    gmb_data = load_json("gmb_post.json")
    if gmb_data:
        post = gmb_data.get("gmb_post", {})
        st.markdown(f"**📍 City:** {gmb_data.get('city', 'N/A')}")
        st.markdown(f"**🎯 Keyword:** `{post.get('keyword_used', 'N/A')}`")
        st.markdown(f"**🏷️ CTA Type:** `{post.get('cta_type', 'N/A')}`")
        st.markdown(f"**📌 Local Signal:** {post.get('local_signal', '')}")
        st.markdown("---")
        st.markdown(post.get("post_body", "No content"))
        pub = gmb_data.get("publish_result", {})
        status_icon = "✅" if pub.get("status") == "published" else "⚠️"
        st.markdown(f"{status_icon} **Publish status:** `{pub.get('status', 'unknown')}`")
    else:
        st.info("No GMB content yet.")

with tab_li:
    li_path = os.path.join(OUTPUT_DIR, "linkedin_post.md")
    if os.path.exists(li_path):
        with open(li_path, encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("No LinkedIn content yet.")

# ── Row 4: Crawl Report ───────────────────────────────────────────────────────
crawl_data = load_json("crawl_report.json")
if crawl_data:
    st.markdown('<div class="section-header">🕷️ Site Crawl Report</div>', unsafe_allow_html=True)
    s = crawl_data.get("summary", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pages Crawled",     s.get("pages_crawled", 0))
    c2.metric("Broken Links",      s.get("broken_links", 0),    delta_color="inverse")
    c3.metric("Pages with Issues", s.get("pages_with_issues", 0), delta_color="inverse")
    c4.metric("Avg Word Count",    s.get("avg_word_count", 0))

    pages = crawl_data.get("pages", [])
    if pages:
        issues_df = pd.DataFrame([
            {"URL": p["url"][:60], "Words": p["word_count"], "Issues": ", ".join(p["issues"]) or "✅ None"}
            for p in pages
        ])
        st.dataframe(issues_df, use_container_width=True, height=200)

# ── Row 5: Deployment + Rank Report ──────────────────────────────────────────
col_dep, col_rank = st.columns(2)

with col_dep:
    st.markdown('<div class="section-header">🚀 Deployment Status</div>', unsafe_allow_html=True)
    if deploy_data:
        st.success(f"Action: **{deploy_data.get('action', 'N/A')}**")
        if deploy_data.get("repo_url"):
            st.markdown(f"🔗 [View on GitHub]({deploy_data['repo_url']})")
        if deploy_data.get("pages_url"):
            st.markdown(f"🌐 [GitHub Pages]({deploy_data['pages_url']})")
    else:
        st.info("Not deployed yet.")

with col_rank:
    st.markdown('<div class="section-header">📊 Rank Report</div>', unsafe_allow_html=True)
    if rank_report:
        gsc = rank_report.get("gsc_data", {})
        st.markdown(f"**Keyword:** `{rank_report.get('keyword', 'N/A')}`")
        st.markdown(f"**Data Source:** `{gsc.get('data_source', 'N/A')}`")
        st.markdown(f"**Period:** {gsc.get('period', 'N/A')}")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Position",    gsc.get("position") or "N/A")
        col_b.metric("CTR",         f"{gsc.get('ctr')}%" if gsc.get("ctr") else "N/A")
        col_c.metric("Impressions", gsc.get("impressions") or "N/A")
    else:
        st.info("No rank data yet.")

st.markdown("---")
st.caption("AI SEO Automation Agent — Built with Groq API + SerpAPI + GSC + GitHub API + Streamlit")
