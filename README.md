# 🤖 AI SEO Automation Agent

> **Rank GMB, Website & LinkedIn content at the top using AI + automation — 100% free tools**

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Groq](https://img.shields.io/badge/AI-Groq_API-orange)](https://console.groq.com)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📋 What This Does

An end-to-end SEO pipeline that:
1. **Keyword Research** — finds high-intent, low-competition keywords per platform (GMB/Website/LinkedIn), scored by difficulty vs volume
2. **Competitor Gap Analysis** — scrapes top-ranking pages, identifies missing content angles via AI
3. **AI Content Generation** — creates SEO-optimised articles (website), GMB posts (localised + NAP-aware), and LinkedIn posts — using Groq API (llama3)
4. **Site Crawl + On-Page Audit** — Screaming Frog alternative, checks broken links, thin content, missing meta, keyword gaps
5. **Auto-Deploy** — pushes generated HTML to GitHub repo via API
6. **Weekly Rank Report** — pulls real CTR/position/impressions from Google Search Console API + logs to Google Sheets

---

## 🏗️ Architecture

```
User Input (Keyword + Platform)
       ↓
┌─ M1: Keyword Research (SerpAPI + BS4 fallback) ─────────────┐
│       ↓ top keywords + scoring                               │
├─ M2: Competitor Analysis (scrape + Groq AI) ────────────────┤
│       ↓ content gaps                                         │
├─ M3a: Website Content (Groq llama3) ────────────────────────┤
├─ M3b: GMB Post (Groq + GMB API + NAP) ─────────────────────┤
├─ M3c: LinkedIn Post (Groq) ─────────────────────────────────┤
│       ↓                                                      │
├─ M4a: Site Crawler (Screaming Frog alt, BFS) ───────────────┤
├─ M4b: SEO Audit (pass/fail score 0-100) ────────────────────┤
│       ↓                                                      │
├─ M5: GitHub Deployment (PyGithub) ─────────────────────────-┤
└─ M6: GSC + Google Sheets Report ────────────────────────────┘
       ↓
Streamlit Live Dashboard
```

---

## 🛠️ Tech Stack & Tool Choices

| Tool | Purpose | Why (Free?) |
|---|---|---|
| **Groq API** (llama3-8b-8192) | All AI generation | Free tier: 30 req/min. Assignment recommended. Fast inference |
| **SerpAPI** | Keyword + SERP data | Free tier: 100 searches/month. Best structured data |
| **BeautifulSoup4** | Web scraping fallback + site crawl | 100% free, no quota |
| **Google Search Console API** | Real rank/CTR/impressions data | Free. Mock data scores lower per assignment |
| **GMB API v4.9** | Publish GMB posts | Free with Google Cloud project |
| **PyGithub** | Auto-deploy HTML to repo | Free for public repos |
| **gspread** | Google Sheets logging | Free: 300 req/min |
| **Streamlit** | Live dashboard | Free Community Cloud hosting |
| **n8n** (self-hosted) | Workflow orchestration | Free open-source (`npx n8n`) |

---

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-seo-agent
cd ai-seo-agent

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
copy .env.example .env
# Now fill in your keys in .env
```

### 3. Run the Pipeline

```bash
# Full pipeline — website content
python main.py --keyword "digital marketing agency" --platform website

# GMB-focused with site crawl
python main.py --keyword "plumber in Mumbai" --platform gmb --site-url https://yoursite.com

# LinkedIn content
python main.py --keyword "LinkedIn growth strategy" --platform linkedin
```

### 4. Launch Dashboard

```bash
streamlit run dashboard/app.py
```

---

## 🔑 API Setup Guide

### Groq API (FREE — 30 req/min)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up → Create API Key
3. Add to `.env`: `GROQ_API_KEY=gsk_...`

### SerpAPI (FREE — 100 searches/month)
1. Go to [serpapi.com](https://serpapi.com)
2. Sign up → copy API key
3. Add to `.env`: `SERPAPI_KEY=...`

### GitHub Token (FREE)
1. GitHub → Settings → Developer Settings → Personal Access Tokens → Classic
2. Select scope: `repo`
3. Add to `.env`: `GITHUB_TOKEN=ghp_...` + `GITHUB_REPO=username/repo`

### Google APIs (FREE — one-time setup)
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project
3. Enable these 3 APIs:
   - **Google Sheets API**
   - **Google Search Console API**
   - **My Business API** (for GMB)
4. Create a **Service Account** → download JSON as `service_account.json` in project root
5. Share your Google Sheet with the service account email (Editor access)
6. Add your site to Google Search Console and verify ownership
7. Fill in `.env`: `GOOGLE_SHEET_ID`, `GSC_SITE_URL`, `GMB_ACCOUNT_ID`, `GMB_LOCATION_ID`

### n8n (FREE — self-hosted)
```bash
npm install -g n8n
npx n8n
# Open http://localhost:5678 → Import n8n/workflow.json
```
> **Note:** n8n is optional — `main.py` runs the same pipeline without it.

---

## 🧪 Test Individual Modules

```bash
# M1 — Keyword Research
python -m modules.keyword_research --keyword "AI tools for marketing" --platform website

# M2 — Competitor Analysis
python -m modules.competitor_analysis --keyword "digital marketing" --urls https://neilpatel.com https://hubspot.com

# M3a — Website Content
python -m modules.content_generator --keyword "AI marketing tools"

# M3b — GMB Content
python -m modules.gmb_content_generator --keyword "digital marketing"

# M3c — LinkedIn Post
python -m modules.linkedin_content_generator --keyword "LinkedIn growth strategy"

# M4a — Site Crawl
python -m modules.site_crawler --url https://yoursite.com --keyword "marketing"

# M4b — SEO Audit
python -m modules.seo_audit

# M6 — Rank Report
python -m modules.reporter --keyword "digital marketing"
```

---

## 📁 Output Files

After running the pipeline, check the `outputs/` folder:

| File | Contents |
|---|---|
| `keyword_report.json` | All keywords with scores, difficulty, platform |
| `competitor_gaps.json` | 5 content gaps identified from competitors |
| `website_content.md` | Full SEO article (1000+ words) |
| `website_content.json` | Article + meta + JSON-LD schema |
| `gmb_post.json` | GMB post content + publish status |
| `linkedin_post.md` | Ready-to-post LinkedIn content |
| `crawl_report.json` | Site-wide crawl: broken links, issues per page |
| `seo_audit.json` | Pass/fail checks + improvement suggestions |
| `deployment_result.json` | GitHub push status + URLs |
| `rank_report.json` | GSC position/CTR/impressions data |

Logs: `logs/seo_agent_YYYYMMDD.log`

---

## ⚠️ Error Handling

- **API failures**: 3-attempt retry with exponential backoff
- **Randomised delays**: 1.5–4.0s between API calls to avoid rate-limits
- **SerpAPI quota**: Auto-switches to BeautifulSoup scraper fallback
- **GSC no data**: Falls back to simulated data with clear labelling
- **GMB API unavailable**: Skips publish, saves content locally
- All failures logged to `logs/errors.log` with module + timestamp

---

## 📖 ≤200 Words: What I'd Improve With More Time / Paid Budget

With more time and a paid budget, I'd make the following improvements:

1. **Ahrefs/Semrush API**: Replace SerpAPI's estimated keyword difficulty with real volume and CPC data from Ahrefs ($99/mo), enabling precision keyword targeting vs our approximation.

2. **Real LinkedIn API posting**: The current implementation exports a ready-to-post file. With LinkedIn Developer App approval and the Marketing API, posts could be published automatically with scheduling and engagement tracking.

3. **Multi-location GMB**: Scale to multiple business locations with batch GMB API calls — critical for franchise or multi-site SEO campaigns.

4. **Continuous ranking tracker**: Add a scheduled weekly job (GitHub Actions cron) to track GSC position changes over time and generate trend charts in the dashboard.

5. **Semantic keyword clustering**: Group keywords by intent (informational/transactional/navigational) using embedding similarity before content generation — would significantly improve content relevance.

6. **Content A/B testing**: Deploy two content variants and track GSC CTR differences to find what ranks better.

7. **Screaming Frog Pro**: Our BFS crawler misses JavaScript-rendered content — Screaming Frog + JS rendering would give a 100% accurate audit.

---

