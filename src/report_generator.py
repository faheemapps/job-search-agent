"""
Daily Report Generator — produces the markdown report exactly per spec
section 15 (Top 20, Top 5 Apply First, High Paying, Best Technical Match,
Dubai/UAE, India Remote) plus the run summary from section 16.
"""
from datetime import datetime, timezone
from . import scoring


def _esc(text):
    """Escape markdown table-breaking characters (pipes, newlines) in
    arbitrary job-title/company text pulled from real listings."""
    if text is None:
        return ""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def _fmt_salary(job):
    if job.get("salary_min"):
        cur = job.get("currency", "")
        low = int(job["salary_min"])
        high = int(job.get("salary_max") or job["salary_min"])
        if low == high:
            return f"{cur} {low:,}"
        return f"{cur} {low:,}-{high:,}"
    return "NOT_AVAILABLE"


def _fmt_posted(job):
    if job.get("posting_date_status") == "VERIFIED" and job.get("posting_date"):
        return job["posting_date"][:10]
    return "UNVERIFIED"


def _row(rank, job):
    skills = ", ".join(job.get("skills", [])[:4]) or "NOT_AVAILABLE"
    return (
        f"| {rank} | {job['match_score']} | {_esc(job['company_name'])} | {_esc(job['job_title'])} | "
        f"{job.get('remote_status','UNKNOWN')} | {_fmt_posted(job)} | {_fmt_salary(job)} | "
        f"{skills} | [Apply]({job['job_url']}) |"
    )


def _top5_detail(job):
    lines = [f"### {_esc(job['company_name'])} — {_esc(job['job_title'])}", ""]
    lines.append(scoring.explain(job).replace("\n", "  \n"))
    lines.append("")
    lines.append(f"- **Salary:** {_fmt_salary(job)} ({job.get('salary_tier','not_disclosed')})")
    lines.append(f"- **Remote eligibility:** {job.get('remote_status','UNKNOWN')} "
                  f"(evidence: _{job.get('remote_status_evidence','n/a')}_)")
    lines.append(f"- **Posted:** {_fmt_posted(job)}")
    lines.append(f"- **Application link:** {job['job_url']}")
    if job.get("company_url"):
        lines.append(f"- **Company careers page:** {job['company_url']}")
    rec_name = job.get("recruiter_name", "NOT_AVAILABLE")
    if rec_name and rec_name != "NOT_AVAILABLE":
        lines.append(f"- **Recruiter/contact:** {rec_name} ({job.get('recruiter_title','NOT_AVAILABLE')}) "
                      f"— {job.get('recruiter_linkedin','NOT_AVAILABLE')}")
    else:
        lines.append("- **Recruiter/contact:** NOT_AVAILABLE")
    lines.append(f"- **Source(s):** {', '.join(sorted({u['source'] for u in job.get('source_urls', [])}))}")
    lines.append("")
    return "\n".join(lines)


def generate_report(jobs: list, run_stats: dict, profile: dict, search_cfg: dict) -> str:
    threshold = search_cfg["run"]["score_threshold_for_report"]
    reportable = [j for j in jobs if j["match_score"] >= threshold]
    ranked = sorted(reportable, key=lambda j: j["rank_score"], reverse=True)

    max_n = search_cfg["run"]["max_jobs_in_report"]
    top20 = ranked[:max_n]
    top5 = ranked[:5]

    high_paying = sorted(
        [j for j in reportable if j.get("salary_min")],
        key=lambda j: (j.get("salary_tier") == "very_high", j.get("salary_max") or j.get("salary_min") or 0),
        reverse=True,
    )[:15]

    def combo_score(j):
        groups = set(j.get("skills", []))
        want = {"snowflake", "informatica_powercenter", "informatica_idmc", "oracle_plsql", "ms_fabric", "airflow"}
        return len(groups & want)

    best_tech = sorted(reportable, key=lambda j: (combo_score(j), j["match_score"]), reverse=True)[:15]

    dubai_uae = [
        j for j in reportable
        if any(k in (j.get("location", "") or "").lower() for k in ["dubai", "uae", "abu dhabi"])
        or j.get("remote_status") == "REMOTE_GLOBAL"
    ][:15]

    india_remote = [j for j in reportable if j.get("remote_status") == "REMOTE_INDIA_CONFIRMED"][:20]

    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")

    out = []
    out.append(f"# Daily Job Search Report — {now}")
    out.append("")
    out.append("## Run Summary")
    out.append("")
    out.append(f"- New jobs found: {run_stats.get('new_jobs_found', 0)}")
    out.append(f"- Total jobs processed this run: {run_stats.get('total_jobs_seen', 0)}")
    out.append(f"- Strong matches (score >= 70): {run_stats.get('strong_matches', 0)}")
    out.append(f"- Excellent matches (score >= 85): {run_stats.get('excellent_matches', 0)}")
    out.append(f"- Jobs posted in last 24h (verified): {run_stats.get('posted_last_24h', 0)}")
    out.append(f"- India-remote confirmed: {run_stats.get('india_remote_confirmed', 0)}")
    out.append(f"- High-paying (high/very high tier): {run_stats.get('high_paying', 0)}")
    out.append("")

    out.append("## TOP 20 JOBS")
    out.append("")
    out.append("| Rank | Score | Company | Role | Remote | Posted | Salary | Key Skills | Apply |")
    out.append("| ---- | ----: | ------- | ---- | ------ | ------ | ------ | ---------- | ----- |")
    for i, j in enumerate(top20, 1):
        out.append(_row(i, j))
    out.append("")

    out.append("## TOP 5 — APPLY FIRST")
    out.append("")
    if not top5:
        out.append("_No jobs cleared the score threshold this run._")
    for j in top5:
        out.append(_top5_detail(j))
    out.append("")

    out.append("## HIGH PAYING JOBS")
    out.append("")
    out.append("| Company | Role | Salary | Remote | Apply |")
    out.append("| ------- | ---- | ------ | ------ | ----- |")
    for j in high_paying:
        out.append(f"| {_esc(j['company_name'])} | {_esc(j['job_title'])} | {_fmt_salary(j)} | {j.get('remote_status')} | [Apply]({j['job_url']}) |")
    if not high_paying:
        out.append("| _none with disclosed salary this run_ | | | | |")
    out.append("")

    out.append("## BEST TECHNICAL MATCH")
    out.append("_Prioritizing Snowflake + Informatica + PL/SQL + Fabric + Airflow combinations_")
    out.append("")
    out.append("| Company | Role | Score | Matched Stack | Apply |")
    out.append("| ------- | ---- | ----: | -------------- | ----- |")
    for j in best_tech:
        stack = ", ".join(j.get("skills", []))
        out.append(f"| {_esc(j['company_name'])} | {_esc(j['job_title'])} | {j['match_score']} | {stack} | [Apply]({j['job_url']}) |")
    out.append("")

    out.append("## DUBAI/UAE & GLOBAL REMOTE")
    out.append("")
    out.append("| Company | Role | Location | Salary | Apply |")
    out.append("| ------- | ---- | -------- | ------ | ----- |")
    for j in dubai_uae:
        out.append(f"| {_esc(j['company_name'])} | {_esc(j['job_title'])} | {_esc(j.get('location','NOT_AVAILABLE'))} | {_fmt_salary(j)} | [Apply]({j['job_url']}) |")
    if not dubai_uae:
        out.append("| _none found this run_ | | | | |")
    out.append("")

    out.append("## INDIA REMOTE (explicitly confirmed)")
    out.append("")
    out.append("| Company | Role | Score | Salary | Apply |")
    out.append("| ------- | ---- | ----: | ------ | ----- |")
    for j in india_remote:
        out.append(f"| {_esc(j['company_name'])} | {_esc(j['job_title'])} | {j['match_score']} | {_fmt_salary(j)} | [Apply]({j['job_url']}) |")
    if not india_remote:
        out.append("| _none explicitly confirmed this run — see UNKNOWN-remote jobs in the full DB for follow-up_ | | | | |")
    out.append("")

    return "\n".join(out)
