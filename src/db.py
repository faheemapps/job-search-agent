"""
SQLite persistence layer for the job search agent.
"""
import sqlite3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "jobs.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = get_connection(path)
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    return conn


def upsert_company(conn, name, website=None, careers_url=None):
    normalized = name.strip().lower()
    row = conn.execute(
        "SELECT company_id FROM companies WHERE normalized_name = ?", (normalized,)
    ).fetchone()
    if row:
        company_id = row["company_id"]
        if careers_url:
            conn.execute(
                "UPDATE companies SET careers_url = COALESCE(careers_url, ?) WHERE company_id = ?",
                (careers_url, company_id),
            )
        return company_id
    cur = conn.execute(
        "INSERT INTO companies (name, normalized_name, website, careers_url, created_at) VALUES (?,?,?,?,?)",
        (name, normalized, website, careers_url, now_iso()),
    )
    return cur.lastrowid


def get_job_by_uid(conn, job_uid):
    return conn.execute("SELECT * FROM jobs WHERE job_uid = ?", (job_uid,)).fetchone()


def insert_or_update_job(conn, job: dict, run_id=None):
    """
    job: normalized dict matching the jobs table columns (see pipeline.py).
    Returns (job_id, is_new: bool)
    """
    existing = get_job_by_uid(conn, job["job_uid"])
    ts = now_iso()

    if existing:
        # merge source_urls, keep first_seen, refresh last_seen/last_verified
        old_sources = json.loads(existing["source_urls_json"] or "[]")
        new_sources = job.get("source_urls", [])
        merged = {u["url"]: u for u in old_sources}
        for u in new_sources:
            merged[u["url"]] = u
        merged_list = list(merged.values())

        conn.execute(
            """UPDATE jobs SET
                job_title=?, normalized_title=?, company_name=?, location=?,
                remote_status=?, remote_status_evidence=?, india_remote_eligible=?,
                posting_date=?, posting_date_status=?, experience_required=?,
                salary_raw=?, salary_min=?, salary_max=?, currency=?, salary_tier=?, salary_source_url=?,
                skills_json=?, job_description=?, job_url=?, company_url=?,
                canonical_source=?, source_urls_json=?,
                recruiter_name=?, recruiter_title=?, recruiter_linkedin=?, recruiter_email=?, email_source=?,
                match_score=?, rank_score=?, score_breakdown_json=?,
                last_seen=?, last_verified=?, search_run_id=?
               WHERE job_uid=?""",
            (
                job["job_title"], job["normalized_title"], job["company_name"], job.get("location"),
                job.get("remote_status"), job.get("remote_status_evidence"), job.get("india_remote_eligible"),
                job.get("posting_date"), job.get("posting_date_status", "UNVERIFIED"), job.get("experience_required"),
                job.get("salary_raw"), job.get("salary_min"), job.get("salary_max"), job.get("currency"),
                job.get("salary_tier"), job.get("salary_source_url"),
                json.dumps(job.get("skills", [])), job.get("job_description"), job.get("job_url"), job.get("company_url"),
                job.get("canonical_source"), json.dumps(merged_list),
                job.get("recruiter_name", "NOT_AVAILABLE"), job.get("recruiter_title", "NOT_AVAILABLE"),
                job.get("recruiter_linkedin", "NOT_AVAILABLE"), job.get("recruiter_email", "NOT_AVAILABLE"),
                job.get("email_source"),
                job.get("match_score", 0), job.get("rank_score", 0), json.dumps(job.get("score_breakdown", {})),
                ts, ts, run_id,
                job["job_uid"],
            ),
        )
        return existing["job_id"], False

    cur = conn.execute(
        """INSERT INTO jobs (
                job_uid, job_title, normalized_title, company_id, company_name, location,
                remote_status, remote_status_evidence, india_remote_eligible,
                posting_date, posting_date_status, experience_required,
                salary_raw, salary_min, salary_max, currency, salary_tier, salary_source_url,
                skills_json, job_description, job_url, company_url,
                canonical_source, source_urls_json, primary_source,
                recruiter_name, recruiter_title, recruiter_linkedin, recruiter_email, email_source,
                match_score, rank_score, score_breakdown_json,
                status, first_seen, last_seen, last_verified, search_run_id
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            job["job_uid"], job["job_title"], job["normalized_title"], job.get("company_id"),
            job["company_name"], job.get("location"),
            job.get("remote_status"), job.get("remote_status_evidence"), job.get("india_remote_eligible"),
            job.get("posting_date"), job.get("posting_date_status", "UNVERIFIED"), job.get("experience_required"),
            job.get("salary_raw"), job.get("salary_min"), job.get("salary_max"), job.get("currency"),
            job.get("salary_tier"), job.get("salary_source_url"),
            json.dumps(job.get("skills", [])), job.get("job_description"), job.get("job_url"), job.get("company_url"),
            job.get("canonical_source"), json.dumps(job.get("source_urls", [])), job.get("primary_source"),
            job.get("recruiter_name", "NOT_AVAILABLE"), job.get("recruiter_title", "NOT_AVAILABLE"),
            job.get("recruiter_linkedin", "NOT_AVAILABLE"), job.get("recruiter_email", "NOT_AVAILABLE"),
            job.get("email_source"),
            job.get("match_score", 0), job.get("rank_score", 0), json.dumps(job.get("score_breakdown", {})),
            "NEW", ts, ts, ts, run_id,
        ),
    )
    return cur.lastrowid, True


def start_search_run(conn, queries, sources):
    cur = conn.execute(
        "INSERT INTO search_runs (started_at, queries_used_json, sources_used_json) VALUES (?,?,?)",
        (now_iso(), json.dumps(queries), json.dumps(sources)),
    )
    conn.commit()
    return cur.lastrowid


def finish_search_run(conn, run_id, stats: dict, errors: list):
    conn.execute(
        """UPDATE search_runs SET finished_at=?, new_jobs_found=?, total_jobs_seen=?,
           strong_matches=?, excellent_matches=?, posted_last_24h=?, india_remote_confirmed=?,
           high_paying=?, errors_json=? WHERE run_id=?""",
        (
            now_iso(), stats.get("new_jobs_found", 0), stats.get("total_jobs_seen", 0),
            stats.get("strong_matches", 0), stats.get("excellent_matches", 0),
            stats.get("posted_last_24h", 0), stats.get("india_remote_confirmed", 0),
            stats.get("high_paying", 0), json.dumps(errors), run_id,
        ),
    )
    conn.commit()
