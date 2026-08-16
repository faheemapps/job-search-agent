"""
Common normalization contract every connector must return so the pipeline
can treat all sources uniformly.

A connector-produced raw job dict should have (values may be None/missing —
the pipeline fills NOT_AVAILABLE where appropriate, never invents data):

{
  "job_title": str,
  "company_name": str,
  "location": str,
  "posting_date": ISO8601 str or None,
  "posting_date_status": "VERIFIED" | "UNVERIFIED",
  "salary_raw": str or None,
  "job_description": str,
  "job_url": str,
  "company_url": str or None,
  "primary_source": str  (matches a name in job_search_config.yaml -> sources),
}
"""
import re
from datetime import datetime, timezone, timedelta


def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def relative_to_iso(days_ago=None, hours_ago=None):
    dt = datetime.now(timezone.utc)
    if days_ago is not None:
        dt -= timedelta(days=days_ago)
    if hours_ago is not None:
        dt -= timedelta(hours=hours_ago)
    return dt.isoformat()
