"""
Application Tracker — never auto-applies. Only records status the candidate
sets explicitly (spec section 13: default behavior is recommend-only).
"""
from datetime import datetime, timezone
from . import db as dbmod

VALID_STATUSES = {"NOT_APPLIED", "APPLY", "APPLIED", "INTERVIEW", "REJECTED", "OFFER", "CLOSED"}


def add_or_update_application(conn, job_id, status="NOT_APPLIED", date_applied=None,
                               recruiter=None, recruiter_contact=None, resume_version=None, notes=None):
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status {status}, must be one of {VALID_STATUSES}")

    job = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if not job:
        raise ValueError(f"no job with job_id={job_id}")

    existing = conn.execute("SELECT * FROM applications WHERE job_id=?", (job_id,)).fetchone()
    ts = datetime.now(timezone.utc).isoformat()

    if existing:
        conn.execute(
            """UPDATE applications SET status=?, date_applied=COALESCE(?, date_applied),
               recruiter=COALESCE(?, recruiter), recruiter_contact=COALESCE(?, recruiter_contact),
               resume_version=COALESCE(?, resume_version), notes=COALESCE(?, notes), updated_at=?
               WHERE job_id=?""",
            (status, date_applied, recruiter, recruiter_contact, resume_version, notes, ts, job_id),
        )
        app_id = existing["application_id"]
    else:
        cur = conn.execute(
            """INSERT INTO applications (job_id, company, role, job_url, date_found, date_applied,
               status, recruiter, recruiter_contact, resume_version, notes, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (job_id, job["company_name"], job["job_title"], job["job_url"], job["first_seen"],
             date_applied, status, recruiter, recruiter_contact, resume_version, notes, ts),
        )
        app_id = cur.lastrowid

    # keep jobs.status in sync for statuses that map directly
    if status in ("APPLIED", "INTERVIEW", "OFFER"):
        conn.execute("UPDATE jobs SET status='APPLIED' WHERE job_id=?", (job_id,))
    elif status == "APPLY":
        conn.execute("UPDATE jobs SET status='SHORTLISTED' WHERE job_id=?", (job_id,))
    elif status == "REJECTED":
        conn.execute("UPDATE jobs SET status='REJECTED' WHERE job_id=?", (job_id,))

    conn.commit()
    return app_id


def list_applications(conn, status=None):
    if status:
        return conn.execute("SELECT * FROM applications WHERE status=? ORDER BY updated_at DESC", (status,)).fetchall()
    return conn.execute("SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
