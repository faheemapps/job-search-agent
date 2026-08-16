"""
Pipeline: normalize raw job dicts (from any connector) -> dedup -> score ->
persist to SQLite -> return summary stats. This is the spine every source
feeds into, regardless of whether it was collected via a free API, an MCP
tool, or an AI-search session.
"""
from datetime import datetime, timezone

from . import dedup, scoring, db as dbmod
from .sources.base import clean_html


def normalize_raw_job(raw: dict) -> dict:
    """Fill required fields with NOT_AVAILABLE rather than inventing data."""
    job = dict(raw)
    job.setdefault("location", "NOT_AVAILABLE")
    job.setdefault("posting_date", None)
    job.setdefault("posting_date_status", "UNVERIFIED")
    job.setdefault("salary_raw", None)
    job.setdefault("job_description", "")
    job.setdefault("company_url", None)
    job["job_description"] = clean_html(job.get("job_description", ""))

    job["normalized_title"] = dedup.normalize_title(job["job_title"])
    job["job_uid"] = dedup.compute_job_uid(job["company_name"], job["job_title"], job.get("location", ""))
    job["source_urls"] = [{"source": job["primary_source"], "url": job["job_url"]}]
    job["canonical_source"] = job["primary_source"]

    job.setdefault("recruiter_name", "NOT_AVAILABLE")
    job.setdefault("recruiter_title", "NOT_AVAILABLE")
    job.setdefault("recruiter_linkedin", "NOT_AVAILABLE")
    job.setdefault("recruiter_email", "NOT_AVAILABLE")
    job.setdefault("email_source", None)
    return job


def dedup_batch(jobs: list, source_priority_order: list, title_thresh: float, desc_thresh: float):
    """Collapse near-duplicate jobs collected within a single run/batch."""
    canonical_list = []
    for job in jobs:
        dup = dedup.find_duplicate(job, canonical_list, title_thresh, desc_thresh)
        if dup:
            merged = dedup.merge_into_canonical(dup, job, source_priority_order)
            canonical_list[canonical_list.index(dup)] = merged
        else:
            canonical_list.append(job)
    return canonical_list


def is_expired(job: dict, max_age_days: int = 45) -> bool:
    """Best-effort expiry check: only mark EXPIRED when we have a verified
    posting date old enough that most listings would have closed. We never
    guess expiry when the date is unverified."""
    if job.get("posting_date_status") != "VERIFIED" or not job.get("posting_date"):
        return False
    try:
        dt = datetime.fromisoformat(job["posting_date"].replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - dt).days
    return age_days > max_age_days


def process_batch(raw_jobs: list, profile: dict, search_cfg: dict, conn, run_id):
    """
    Full pipeline for one batch of raw jobs collected in a run:
    normalize -> dedup (within batch) -> score -> dedup against DB (via
    job_uid upsert) -> persist -> return stats.
    """
    normalized = [normalize_raw_job(r) for r in raw_jobs]

    src_cfg = search_cfg["dedup"]
    deduped = dedup_batch(
        normalized,
        search_cfg["source_priority_order"],
        src_cfg["title_similarity_threshold"],
        src_cfg["description_similarity_threshold"],
    )

    scored = [scoring.score_job(j, profile, search_cfg) for j in deduped]

    stats = {
        "total_jobs_seen": len(scored),
        "new_jobs_found": 0,
        "strong_matches": 0,
        "excellent_matches": 0,
        "posted_last_24h": 0,
        "india_remote_confirmed": 0,
        "high_paying": 0,
    }

    persisted = []
    for job in scored:
        if is_expired(job):
            job["status_override"] = "EXPIRED"

        job_id, is_new = dbmod.insert_or_update_job(conn, job, run_id=run_id)
        if is_new:
            stats["new_jobs_found"] += 1
        if job["match_score"] >= 70:
            stats["strong_matches"] += 1
        if job["match_score"] >= 85:
            stats["excellent_matches"] += 1
        if job.get("recency_tier") == "tier1_24h":
            stats["posted_last_24h"] += 1
        if job.get("remote_status") == "REMOTE_INDIA_CONFIRMED":
            stats["india_remote_confirmed"] += 1
        if job.get("salary_tier") in ("very_high", "high"):
            stats["high_paying"] += 1

        job["job_id"] = job_id
        persisted.append(job)

    conn.commit()
    return persisted, stats
