"""
No-auth-required public JSON APIs for remote jobs. These connectors use
Python's `requests` directly and are fully headless-automatable (no Claude
tools needed) -- suitable for a plain cron job or GitHub Actions runner with
normal internet access.

NOTE: Anthropic's cloud sandbox that this project may have been *built* in
restricts arbitrary outbound HTTP from Python (allowlisted egress only), so
these connectors will return a clear error there. They work normally on a
regular machine / CI runner. When running inside a Claude session without
open egress, use the `ai_search` connectors instead (src/sources/ai_search.py)
which route requests through Claude's WebSearch/WebFetch tools.
"""
import requests
from .base import clean_html

HEADERS = {"User-Agent": "job-search-agent/1.0 (personal use; contact via profile)"}
TIMEOUT = 20


def fetch_remotive(query: str, limit: int = 15):
    url = "https://remotive.com/api/remote-jobs"
    r = requests.get(url, params={"search": query, "limit": limit}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json().get("jobs", []):
        jobs.append({
            "job_title": j.get("title"),
            "company_name": j.get("company_name"),
            "location": j.get("candidate_required_location"),
            "posting_date": j.get("publication_date"),
            "posting_date_status": "VERIFIED" if j.get("publication_date") else "UNVERIFIED",
            "salary_raw": j.get("salary") or None,
            "job_description": clean_html(j.get("description", "")),
            "job_url": j.get("url"),
            "company_url": j.get("company_url") or None,
            "primary_source": "Remotive",
        })
    return jobs


def fetch_remoteok(query: str, limit: int = 15):
    url = "https://remoteok.com/api"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    jobs = []
    q_terms = [t.lower() for t in query.split()]
    for j in data:
        if not isinstance(j, dict) or "position" not in j:
            continue
        text = f"{j.get('position','')} {j.get('description','')}".lower()
        if not any(t in text for t in q_terms):
            continue
        jobs.append({
            "job_title": j.get("position"),
            "company_name": j.get("company"),
            "location": j.get("location") or "Remote",
            "posting_date": j.get("date"),
            "posting_date_status": "VERIFIED" if j.get("date") else "UNVERIFIED",
            "salary_raw": f"{j.get('salary_min','')}-{j.get('salary_max','')}" if j.get("salary_min") else None,
            "job_description": clean_html(j.get("description", "")),
            "job_url": f"https://remoteok.com/remote-jobs/{j.get('id')}" if j.get("id") else j.get("url"),
            "company_url": j.get("company_url") or None,
            "primary_source": "RemoteOK",
        })
        if len(jobs) >= limit:
            break
    return jobs


def fetch_arbeitnow(query: str, limit: int = 15):
    url = "https://www.arbeitnow.com/api/job-board-api"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json().get("data", [])
    jobs = []
    q_terms = [t.lower() for t in query.split()]
    for j in data:
        text = f"{j.get('title','')} {j.get('description','')}".lower()
        if not any(t in text for t in q_terms):
            continue
        jobs.append({
            "job_title": j.get("title"),
            "company_name": j.get("company_name"),
            "location": j.get("location") or ("Remote" if j.get("remote") else ""),
            "posting_date": None,
            "posting_date_status": "UNVERIFIED",
            "salary_raw": None,
            "job_description": clean_html(j.get("description", "")),
            "job_url": j.get("url"),
            "company_url": None,
            "primary_source": "Arbeitnow",
        })
        if len(jobs) >= limit:
            break
    return jobs


def fetch_jobicy(query: str, limit: int = 15):
    url = "https://jobicy.com/api/v2/remote-jobs"
    r = requests.get(url, params={"count": limit, "tag": "data"}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json().get("jobs", []):
        jobs.append({
            "job_title": j.get("jobTitle"),
            "company_name": j.get("companyName"),
            "location": j.get("jobGeo"),
            "posting_date": j.get("pubDate"),
            "posting_date_status": "VERIFIED" if j.get("pubDate") else "UNVERIFIED",
            "salary_raw": j.get("annualSalaryMin") and f"{j.get('annualSalaryMin')}-{j.get('annualSalaryMax')} {j.get('salaryCurrency','')}",
            "job_description": clean_html(j.get("jobExcerpt", "")),
            "job_url": j.get("url"),
            "company_url": None,
            "primary_source": "Jobicy",
        })
    return jobs


def fetch_himalayas(query: str, limit: int = 15):
    url = "https://himalayas.app/jobs/api"
    r = requests.get(url, params={"limit": limit}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json().get("jobs", []):
        jobs.append({
            "job_title": j.get("title"),
            "company_name": (j.get("companyName") or j.get("company", {}).get("name")),
            "location": ", ".join(j.get("locationRestrictions", []) or []) or "Remote",
            "posting_date": j.get("pubDate"),
            "posting_date_status": "VERIFIED" if j.get("pubDate") else "UNVERIFIED",
            "salary_raw": None,
            "job_description": clean_html(j.get("description", "")),
            "job_url": j.get("applicationLink") or j.get("guid"),
            "company_url": None,
            "primary_source": "Himalayas",
        })
    return jobs


CONNECTORS = {
    "Remotive": fetch_remotive,
    "RemoteOK": fetch_remoteok,
    "Arbeitnow": fetch_arbeitnow,
    "Jobicy": fetch_jobicy,
    "Himalayas": fetch_himalayas,
}


def fetch_all(query: str, limit: int, enabled_sources: list, errors: list):
    """Calls every enabled API connector; a failure in one never stops the
    others (spec section 21 — one failed source must not stop the search)."""
    results = []
    for name, fn in CONNECTORS.items():
        if name not in enabled_sources:
            continue
        try:
            results.extend(fn(query, limit))
        except Exception as e:  # noqa: BLE001 - intentionally broad, logged not raised
            errors.append({"source": name, "query": query, "error": str(e)})
    return results
