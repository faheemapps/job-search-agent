#!/usr/bin/env python3
"""
AI Job Search Agent — CLI orchestrator.

Usage:
    python3 main.py init
    python3 main.py run-free-apis [--limit 15]
    python3 main.py ingest data/raw/linkedin_2026-08-15.json
    python3 main.py report [--out reports/2026-08-15.md]
    python3 main.py track --job-id 12 --status APPLY --notes "great fit"
    python3 main.py list-applications [--status APPLY]
    python3 main.py stats
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import db as dbmod
from src import config_loader
from src import pipeline
from src import query_generator
from src import report_generator
from src import tracker
from src import alerts
from src.sources import free_apis

ROOT = Path(__file__).resolve().parent


def cmd_init(args):
    conn = dbmod.init_db()
    profile = config_loader.load_profile()
    conn.execute(
        "INSERT OR REPLACE INTO candidate_profile (id, profile_yaml, loaded_at) VALUES (1, ?, ?)",
        (json.dumps(profile), dbmod.now_iso()),
    )
    conn.commit()
    print(f"Initialized database at {dbmod.DB_PATH}")


def cmd_run_free_apis(args):
    """Runs the no-auth public JSON API connectors directly. Requires normal
    outbound internet access (works in GitHub Actions / a regular machine;
    will raise clear per-source errors in network-restricted sandboxes)."""
    profile = config_loader.load_profile()
    search_cfg = config_loader.load_search_config()
    conn = dbmod.get_connection()

    discovered = query_generator.load_discovered_terms()
    queries = query_generator.generate_queries(search_cfg["seed_queries"], discovered)

    enabled_api_sources = [s["name"] for s in search_cfg["sources"] if s["type"] == "api" and s["enabled"]]
    run_id = dbmod.start_search_run(conn, queries, enabled_api_sources)

    all_raw = []
    errors = []
    for q in queries:
        all_raw.extend(free_apis.fetch_all(q, args.limit, enabled_api_sources, errors))

    persisted, stats = pipeline.process_batch(all_raw, profile, search_cfg, conn, run_id)
    dbmod.finish_search_run(conn, run_id, stats, errors)

    titles = [j["job_title"] for j in persisted]
    new_terms = query_generator.discover_terms_from_titles(titles)
    if new_terms:
        query_generator.save_discovered_terms(discovered + new_terms)

    print(f"Run #{run_id}: {stats}")
    if errors:
        print(f"{len(errors)} source errors (non-fatal), see search_runs.errors_json for run #{run_id}")
    for j in persisted:
        for name in alerts.evaluate_alerts(j, profile):
            print(f"ALERT[{name}] {j['company_name']} — {j['job_title']} (score {j['match_score']}) {j['job_url']}")


def cmd_ingest(args):
    """Ingests a pre-collected raw-jobs JSON file (produced by a Claude
    session's WebSearch/MCP-tool run, or by any connector) through the same
    normalize -> dedup -> score -> persist pipeline."""
    profile = config_loader.load_profile()
    search_cfg = config_loader.load_search_config()
    conn = dbmod.get_connection()

    with open(args.file) as f:
        raw_jobs = json.load(f)

    from src.sources.ai_search import validate_raw_job
    valid, invalid = [], []
    for r in raw_jobs:
        errs = validate_raw_job(r)
        if errs:
            invalid.append((r.get("job_title", "?"), errs))
        else:
            valid.append(r)

    if invalid:
        print(f"Skipped {len(invalid)} invalid records:")
        for title, errs in invalid[:10]:
            print(f"  - {title}: {errs}")

    sources_used = sorted({r["primary_source"] for r in valid})
    run_id = dbmod.start_search_run(conn, [args.file], sources_used)
    persisted, stats = pipeline.process_batch(valid, profile, search_cfg, conn, run_id)
    dbmod.finish_search_run(conn, run_id, stats, [])

    titles = [j["job_title"] for j in persisted]
    discovered = query_generator.load_discovered_terms()
    new_terms = query_generator.discover_terms_from_titles(titles)
    if new_terms:
        query_generator.save_discovered_terms(discovered + new_terms)

    print(f"Ingested {args.file}: run #{run_id}, stats={stats}")
    for j in persisted:
        for name in alerts.evaluate_alerts(j, profile):
            print(f"ALERT[{name}] {j['company_name']} — {j['job_title']} (score {j['match_score']}) {j['job_url']}")


def cmd_report(args):
    profile = config_loader.load_profile()
    search_cfg = config_loader.load_search_config()
    conn = dbmod.get_connection()

    rows = conn.execute("SELECT * FROM jobs WHERE status != 'REJECTED'").fetchall()
    jobs = []
    for row in rows:
        j = dict(row)
        j["skills"] = json.loads(j["skills_json"] or "[]")
        j["score_breakdown"] = json.loads(j["score_breakdown_json"] or "{}")
        j["source_urls"] = json.loads(j["source_urls_json"] or "[]")
        jobs.append(j)

    last_run = conn.execute("SELECT * FROM search_runs ORDER BY run_id DESC LIMIT 1").fetchone()
    run_stats = dict(last_run) if last_run else {}

    md = report_generator.generate_report(jobs, run_stats, profile, search_cfg)

    out_path = Path(args.out) if args.out else ROOT / "reports" / "latest_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"Report written to {out_path}")


def cmd_track(args):
    conn = dbmod.get_connection()
    app_id = tracker.add_or_update_application(
        conn, args.job_id, status=args.status, date_applied=args.date_applied,
        recruiter=args.recruiter, recruiter_contact=args.recruiter_contact,
        resume_version=args.resume_version, notes=args.notes,
    )
    print(f"Application #{app_id} updated for job #{args.job_id} -> {args.status}")


def cmd_list_applications(args):
    conn = dbmod.get_connection()
    rows = tracker.list_applications(conn, status=args.status)
    for r in rows:
        print(f"[{r['status']}] job#{r['job_id']} {r['company']} — {r['role']} | applied={r['date_applied']} | {r['job_url']}")


def cmd_stats(args):
    conn = dbmod.get_connection()
    total = conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"]
    by_status = conn.execute("SELECT status, COUNT(*) c FROM jobs GROUP BY status").fetchall()
    by_remote = conn.execute("SELECT remote_status, COUNT(*) c FROM jobs GROUP BY remote_status").fetchall()
    print(f"Total jobs in DB: {total}")
    print("By status:", {r["status"]: r["c"] for r in by_status})
    print("By remote status:", {r["remote_status"]: r["c"] for r in by_remote})


def build_parser():
    p = argparse.ArgumentParser(description="AI Job Search Agent")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    sp = sub.add_parser("run-free-apis")
    sp.add_argument("--limit", type=int, default=15)
    sp.set_defaults(func=cmd_run_free_apis)

    sp = sub.add_parser("ingest")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("report")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("track")
    sp.add_argument("--job-id", type=int, required=True)
    sp.add_argument("--status", required=True, choices=list(tracker.VALID_STATUSES))
    sp.add_argument("--date-applied", default=None)
    sp.add_argument("--recruiter", default=None)
    sp.add_argument("--recruiter-contact", default=None)
    sp.add_argument("--resume-version", default=None)
    sp.add_argument("--notes", default=None)
    sp.set_defaults(func=cmd_track)

    sp = sub.add_parser("list-applications")
    sp.add_argument("--status", default=None)
    sp.set_defaults(func=cmd_list_applications)

    sub.add_parser("stats").set_defaults(func=cmd_stats)

    return p


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
