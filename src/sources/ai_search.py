"""
AI-Search-Assisted Connector Contract
======================================
LinkedIn, Naukri, Naukri Gulf, Glassdoor, Bayt, Foundit, Wellfound,
Instahyre, individual company career pages, and general Google/web search
have no free public API and most disallow automated scraping in
robots.txt. For these sources the pipeline relies on a *Claude session*
performing WebSearch (and WebFetch only where a target page's robots.txt
permits it) and writing results into data/raw/<source>_<timestamp>.json
using the schema below. This keeps the heavy-lifting (dedup, scoring,
ranking, storage, reporting) in deterministic, testable Python while
respecting each site's terms of service.

This module does not perform any network calls itself — it only defines
the contract and a validator so ingestion is consistent no matter which
source produced the file.

Expected JSON file shape:
[
  {
    "job_title": "...",
    "company_name": "...",
    "location": "...",                 # raw text as seen on the listing
    "posting_date": "2026-08-14" | null,   # ISO date, ONLY if explicitly stated by the source
    "posting_date_status": "VERIFIED" | "UNVERIFIED",
    "salary_raw": "..." | null,        # verbatim salary text if shown, else null
    "job_description": "...",          # as much of the actual description/snippet as available
    "job_url": "https://...",          # the actual listing URL (never invented)
    "company_url": "https://..." | null,
    "primary_source": "LinkedIn" | "Naukri" | "NaukriGulf" | "Glassdoor" | "Bayt"
                       | "Foundit" | "Wellfound" | "Instahyre" | "CompanyCareerPage"
                       | "GoogleWebSearch",
    "search_query": "the query that surfaced this result"
  },
  ...
]
"""

REQUIRED_FIELDS = ["job_title", "company_name", "job_url", "primary_source"]


def validate_raw_job(raw: dict) -> list:
    """Returns a list of validation error strings (empty list = valid).
    Enforces anti-hallucination rule: job_url must be present and must look
    like a real URL — the agent must never invent one."""
    errors = []
    for f in REQUIRED_FIELDS:
        if not raw.get(f):
            errors.append(f"missing required field: {f}")
    url = raw.get("job_url", "")
    if url and not (url.startswith("http://") or url.startswith("https://")):
        errors.append(f"job_url does not look like a real URL: {url!r}")
    if raw.get("posting_date") and raw.get("posting_date_status") != "VERIFIED":
        errors.append("posting_date set but posting_date_status is not VERIFIED")
    return errors
