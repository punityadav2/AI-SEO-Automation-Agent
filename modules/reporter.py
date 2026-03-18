"""
modules/reporter.py — Module 6: Reporting (Google Search Console + Google Sheets)
- Pulls REAL ranking data from Google Search Console API
- Logs all run metrics to Google Sheets
- Outputs rank_report.json
"""

import json
import os
from datetime import datetime, timedelta

import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build

import config
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger(__name__)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]
SERVICE_ACCOUNT_FILE = "service_account.json"

SHEET_HEADERS = [
    "Date", "Keyword", "Platform", "Avg Position",
    "CTR (%)", "Impressions", "Clicks",
    "Content Title", "Audit Score", "GitHub URL", "GMB Status", "Status"
]


def _get_credentials():
    """Load Google service account credentials."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.warning(f"{SERVICE_ACCOUNT_FILE} not found — Google API calls skipped.")
        return None
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )


# ── Google Search Console ─────────────────────────────────────────────────────
@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _fetch_gsc_data(keyword: str) -> dict:
    """
    Pull real ranking data from Google Search Console API for the target keyword.
    Returns position, CTR, impressions, clicks for the past 7 days.
    """
    creds = _get_credentials()
    if not creds or not config.GSC_SITE_URL:
        logger.warning("GSC credentials or site URL not set — using simulated data.")
        return _simulated_gsc_data(keyword)

    service = build("searchconsole", "v1", credentials=creds)

    end_date   = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    request_body = {
        "startDate":    start_date.isoformat(),
        "endDate":      end_date.isoformat(),
        "dimensions":   ["query"],
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension":  "query",
                "operator":   "contains",
                "expression": keyword,
            }]
        }],
        "rowLimit": 10,
    }

    response = service.searchanalytics().query(
        siteUrl=config.GSC_SITE_URL,
        body=request_body,
    ).execute()

    rows = response.get("rows", [])
    if not rows:
        logger.info(f"No GSC data found for keyword '{keyword}' — may not be indexed yet.")
        return _simulated_gsc_data(keyword, note="not_indexed_yet")

    # Aggregate across all matching queries
    total_impressions = sum(r.get("impressions", 0) for r in rows)
    total_clicks      = sum(r.get("clicks", 0) for r in rows)
    avg_position      = sum(r.get("position", 0) for r in rows) / len(rows)
    avg_ctr           = (total_clicks / total_impressions * 100) if total_impressions else 0

    return {
        "keyword":     keyword,
        "period":      f"{start_date} to {end_date}",
        "position":    round(avg_position, 1),
        "ctr":         round(avg_ctr, 2),
        "impressions": total_impressions,
        "clicks":      total_clicks,
        "data_source": "Google Search Console API (live)",
        "rows":        rows[:5],
    }


def _simulated_gsc_data(keyword: str, note: str = "credentials_not_set") -> dict:
    """Fallback simulated data when GSC API is unavailable."""
    logger.info(f"Using simulated GSC data for '{keyword}' (note: {note})")
    return {
        "keyword":     keyword,
        "period":      "last 7 days",
        "position":    None,
        "ctr":         None,
        "impressions": None,
        "clicks":      None,
        "data_source": f"SIMULATED ({note})",
        "note":        "Connect GSC API for real data. See README → Google Search Console Setup.",
    }


# ── Google Sheets ─────────────────────────────────────────────────────────────
@retry(max_attempts=config.RETRY_MAX_ATTEMPTS, backoff=config.RETRY_BACKOFF_SECS)
def _append_to_sheet(row_data: list) -> bool:
    """Append a row to the Google Sheet. Creates headers if sheet is empty."""
    creds = _get_credentials()
    if not creds or not config.GOOGLE_SHEET_ID:
        logger.warning("Google Sheets not configured — skipping sheet update.")
        return False

    gc         = gspread.authorize(creds)
    sheet      = gc.open_by_key(config.GOOGLE_SHEET_ID)
    worksheet  = sheet.sheet1

    # Add headers if sheet is empty
    if worksheet.row_count == 0 or not worksheet.row_values(1):
        worksheet.append_row(SHEET_HEADERS)
        logger.info("  Google Sheet headers created.")

    worksheet.append_row(row_data)
    logger.info(f"  Row appended to Google Sheet: {row_data[0]} | {row_data[1]}")
    return True


# ── Main public function ──────────────────────────────────────────────────────
def run(
    keyword:     str,
    platform:    str = "website",
    content_title: str = "",
    audit_score: float = 0.0,
    github_url:  str = "",
    gmb_status:  str = "",
) -> dict:
    """
    Fetch rankings from GSC and log everything to Google Sheets.

    Args:
        keyword       : Primary keyword.
        platform      : 'website', 'gmb', or 'linkedin'.
        content_title : Title of the generated content.
        audit_score   : SEO audit score (0-100).
        github_url    : URL of the deployed content.
        gmb_status    : GMB publish status.

    Returns:
        Rank report dict, saved to outputs/rank_report.json.
    """
    logger.info(f"▶ Reporting | keyword='{keyword}'")

    # Pull GSC data
    gsc_data = _fetch_gsc_data(keyword)

    # Build report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = {
        "timestamp":     timestamp,
        "keyword":       keyword,
        "platform":      platform,
        "gsc_data":      gsc_data,
        "content_title": content_title,
        "audit_score":   audit_score,
        "github_url":    github_url,
        "gmb_status":    gmb_status,
        "status":        "success",
    }

    # Append to Google Sheets
    row = [
        timestamp,
        keyword,
        platform,
        gsc_data.get("position") or "N/A",
        gsc_data.get("ctr") or "N/A",
        gsc_data.get("impressions") or "N/A",
        gsc_data.get("clicks") or "N/A",
        content_title,
        audit_score,
        github_url,
        gmb_status,
        "success",
    ]
    _append_to_sheet(row)

    # Save JSON report
    out_path = os.path.join(config.OUTPUT_DIR, "rank_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(
        f"✅ Report saved → {out_path} | "
        f"GSC Position: {gsc_data.get('position', 'N/A')} | "
        f"Source: {gsc_data.get('data_source')}"
    )
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True)
    args = parser.parse_args()
    report = run(args.keyword)
    print(f"\nRank Report: {json.dumps(report['gsc_data'], indent=2)}")
