"""
config.py — Centralised configuration for AI SEO Automation Agent
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ─────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
SERPAPI_KEY     = os.getenv("SERPAPI_KEY", "")
GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO     = os.getenv("GITHUB_REPO", "")

# ── Google ───────────────────────────────────────────────────
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GSC_SITE_URL    = os.getenv("GSC_SITE_URL", "")
GMB_ACCOUNT_ID  = os.getenv("GMB_ACCOUNT_ID", "")
GMB_LOCATION_ID = os.getenv("GMB_LOCATION_ID", "")

# ── Content Settings ─────────────────────────────────────────
TARGET_CITY     = os.getenv("TARGET_CITY", "Mumbai")
TARGET_INDUSTRY = os.getenv("TARGET_INDUSTRY", "digital marketing")

# ── Groq Model ───────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
 # Free tier model

# ── Rate Limiting ─────────────────────────────────────────────
RETRY_MAX_ATTEMPTS  = 3
RETRY_BACKOFF_SECS  = 2          # doubles each retry
DELAY_MIN_SECS      = 1.5        # randomised delay between API calls
DELAY_MAX_SECS      = 4.0

# ── Keyword Scoring ──────────────────────────────────────────
TOP_KEYWORDS_TO_USE = 5          # How many top keywords to pass downstream
MIN_KEYWORD_SCORE   = 0.1        # Drop keywords below this score

# ── Audit Thresholds ─────────────────────────────────────────
MIN_CONTENT_WORDS   = 800
IDEAL_KEYWORD_DENSITY_MIN = 0.01  # 1%
IDEAL_KEYWORD_DENSITY_MAX = 0.03  # 3%
META_TITLE_MAX      = 60
META_DESC_MAX       = 160

# ── Output Paths ─────────────────────────────────────────────
OUTPUT_DIR = "outputs"
LOG_DIR    = "logs"
