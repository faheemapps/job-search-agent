# AI Job Search Agent — Remote Data Engineering Roles

A modular, production-quality job search agent for Snowflake / Informatica /
Oracle PL/SQL / data-warehouse profiles, built and tested end-to-end in this
environment (not a mock). It searches, extracts, verifies remote eligibility
for India, scores, deduplicates, ranks, and produces a daily shortlist —
without ever inventing salary, recruiter, or remote-eligibility data.

## 1. How data actually gets collected here (read this first)

This project was built and demonstrated inside a Claude session. That
session's Python sandbox has **allowlisted, restricted outbound network
access** — direct `requests` calls to most public job-board domains are
blocked there (confirmed while building this: Remotive/RemoteOK/Arbeitnow/
Jobicy/Himalayas/WeWorkRemotely all returned `403` through the sandbox
egress proxy). Two things remain true and are what this project relies on:

1. **`src/sources/free_apis.py`** (Remotive, RemoteOK, Arbeitnow, Jobicy,
   Himalayas) is real, working code that calls genuine no-auth-required
   public JSON APIs. It will run headlessly with a normal internet
   connection — a laptop, a server, or a GitHub Actions runner (see the
   included workflow). It could not be exercised against live traffic
   *inside the Claude sandbox itself*, only inside a normal runner.
2. **LinkedIn, Naukri, Naukri Gulf, Glassdoor, Bayt, Foundit, Wellfound,
   Instahyre, individual company career pages, and general Google search**
   have no public search APIs, and most disallow automated `/jobs`
   scraping in `robots.txt`. Per your instructions, this agent does not
   attempt to bypass that. Instead, a Claude session performs `WebSearch`
   (and `WebFetch` only where a target page's `robots.txt` allows it),
   normalizes results into the schema in `src/sources/ai_search.py`, and
   feeds them through `python3 main.py ingest <file>` — the exact same
   scoring/dedup/ranking pipeline every other source uses.
3. **Indeed, Dice, and ZipRecruiter** are reached through first-party MCP
   tool connectors available in the Claude session (not blocked by the
   sandbox's HTTP egress policy, since they're not raw HTTP calls). A
   Claude session calls them, then feeds normalized results into the same
   `ingest` pipeline.

This hybrid design is what real reliability constraints in this environment
actually allow — see `config/job_search_config.yaml -> sources[].type` for
the full connector-by-connector breakdown (`api`, `mcp_tool`, `ai_search`).

## 2. Architecture

```
job_search_agent/
├── config/
│   ├── candidate_profile.yaml      # your skills, roles, salary target — EDIT THIS
│   └── job_search_config.yaml      # scoring weights, sources, thresholds, queries
├── db/
│   ├── schema.sql                  # jobs, companies, contacts, job_sources,
│   │                                #   applications, search_runs, candidate_profile
│   └── jobs.db                     # SQLite DB (created by `main.py init`)
├── src/
│   ├── config_loader.py
│   ├── query_generator.py          # seed + dynamically-discovered search queries
│   ├── skill_matcher.py            # synonym-aware skill matching + seniority/experience scoring
│   ├── remote_verifier.py          # REMOTE_INDIA_CONFIRMED / REMOTE_GLOBAL / ... classifier
│   ├── salary_extractor.py         # regex salary parsing + tiering (never invents figures)
│   ├── dedup.py                    # cross-source duplicate detection & merge
│   ├── scoring.py                  # 0-100 rubric + bonus/recency ranking score
│   ├── recruiter_discovery.py      # query templates + anti-fabrication validator
│   ├── alerts.py                   # high-priority alert rules
│   ├── pipeline.py                 # normalize -> dedup -> score -> persist
│   ├── report_generator.py         # builds the daily markdown report
│   ├── tracker.py                  # application tracker (never auto-applies)
│   ├── db.py                       # SQLite access layer
│   └── sources/
│       ├── base.py                 # shared normalization helpers
│       ├── free_apis.py            # Remotive/RemoteOK/Arbeitnow/Jobicy/Himalayas (real API calls)
│       └── ai_search.py            # ingestion contract/validator for WebSearch/MCP-collected jobs
├── data/
│   └── raw/                        # raw ingestion JSON files land here
├── reports/                        # generated daily markdown reports
├── tests/                          # unit tests (20 passing, see section 8)
├── main.py                         # CLI entrypoint
├── requirements.txt
└── .github/workflows/daily_job_search.yml   # free-API sources, fully unattended
```

Every module is independently importable/testable — `src/skill_matcher.py`,
`src/remote_verifier.py`, `src/salary_extractor.py`, `src/dedup.py`, and
`src/scoring.py` have no dependency on the database or network layer.

## 3. Install & initialize

```bash
cd job_search_agent
pip install -r requirements.txt
python3 main.py init          # creates db/jobs.db from db/schema.sql
```

## 4. Running it

### 4a. Free-API sources only (fully headless, no Claude needed)
```bash
python3 main.py run-free-apis --limit 20
python3 main.py report --out reports/$(date +%F).md
```

### 4b. Full-coverage run (LinkedIn/Naukri/Glassdoor/Bayt/Foundit/Wellfound/
Instahyre/company pages/Indeed/Dice/ZipRecruiter) — ask a Claude session to:
1. Read `config/job_search_config.yaml -> seed_queries` and
   `data/discovered_terms.json`.
2. For each `ai_search` source, run `WebSearch` with the query templates
   (append `site:linkedin.com/jobs`, `site:naukri.com`, `site:bayt.com`,
   etc. as needed) and extract job postings — never fabricating a URL,
   date, or salary that isn't actually shown.
3. Call the `Indeed` / `Dice` / `ZipRecruiter` MCP tools directly for those
   three sources.
4. Write everything to `data/raw/<source>_<date>.json` matching the schema
   documented in `src/sources/ai_search.py`.
5. Run `python3 main.py ingest data/raw/<file>.json` for each file (or a
   combined file).
6. Run `python3 main.py report`.

This is exactly the process used to produce the example run in section 9.

### 4c. Recording your own application activity
```bash
python3 main.py track --job-id 4 --status APPLY --notes "Strong match, applying tonight"
python3 main.py track --job-id 4 --status APPLIED --date-applied 2026-08-16 --resume-version "resume_v3_snowflake.pdf"
python3 main.py list-applications --status APPLY
```
The agent **never applies automatically** — `auto_apply_enabled: false` in
`job_search_config.yaml` is the single flag that would need to change, and
this codebase does not implement the submission step even if it were
flipped, by design (spec requirement).

## 5. Scheduling daily runs

You asked for the most reliable mechanism actually available. Two real
options, be clear-eyed about what each covers:

**Option A — GitHub Actions (`.github/workflows/daily_job_search.yml`, included):**
fully unattended, runs `run-free-apis` daily at 08:00 IST, commits the
updated DB + report back to your repo. Zero ongoing Claude usage. Only
covers the free-API sources (Remotive, RemoteOK, Arbeitnow, Jobicy,
Himalayas) — good breadth of genuinely remote listings, but not
LinkedIn/Naukri/Indeed/etc.
1. Push this project to a GitHub repo.
2. Enable Actions.
3. Done — first run fires on the next scheduled tick, or trigger manually
   via "Run workflow".

**Option B — a Claude scheduled task, for full source coverage:** create a
daily trigger whose prompt tells a fresh Claude session to `git clone` your
repo (so it has the persistent DB), perform the WebSearch/MCP-tool searches
described in 4b, `git commit` the updated DB and report, and message you the
top results. This is the only way to get LinkedIn/Naukri/Glassdoor/etc.
coverage on a schedule, because those connectors require Claude's WebSearch
and MCP tools, which don't exist in a plain cron job. Ask Claude to set this
up for you with `create_trigger` once your repo exists — it needs the repo
URL and a way to push (e.g. a fine-grained PAT stored as a secret you
provide at trigger-creation time, never hardcoded in this codebase).

Realistically: run A nightly for baseline coverage, and B weekly (or
on-demand) for the deeper multi-board sweep — both write to the same
`db/jobs.db`, so the report always reflects everything found so far.

## 6. Changing your profile without touching code

Edit `config/candidate_profile.yaml`:
- **Skills:** edit `core_skills` / `secondary_skills`. To teach the matcher
  new synonyms (e.g. a new tool name), add a group to
  `job_search_config.yaml -> skill_synonyms`.
- **Salary:** edit `minimum_target_salary` (by currency code) in
  `candidate_profile.yaml`, and the tier cutoffs in
  `job_search_config.yaml -> salary_thresholds`.
- **Target roles / locations:** edit `target_roles`,
  `international_remote_locations`, `primary_work_location`.
- **Experience:** edit `experience_years` — flows straight into the
  Experience score bucket.

## 7. Adding a new job source

1. Add an entry under `sources:` in `job_search_config.yaml` with a `type`
   of `api`, `mcp_tool`, or `ai_search`, plus a `priority` (used for
   dedup's "prefer the more trusted source" rule — see
   `source_priority_order`).
2. If `type: api`: add a `fetch_<source>(query, limit)` function to
   `src/sources/free_apis.py` returning the schema in `src/sources/base.py`,
   and register it in the `CONNECTORS` dict.
3. If `type: mcp_tool` or `ai_search`: no code changes needed — a Claude
   session collects results and writes them to `data/raw/*.json` per
   `src/sources/ai_search.py`'s schema, then `python3 main.py ingest <file>`.

## 8. Tests

```bash
python3 -m unittest discover -s tests -v
```
20 tests, all passing, covering: skill-synonym matching (Informatica,
PL/SQL, Airflow, Fabric variants), false-positive avoidance, seniority/
experience bucketing, all 6 remote-status classifications, cross-source
deduplication + canonical-source merge logic, and score-rubric correctness
(strong match ≥85, weak match <30, hard cap at 100).

## 9. Example output

See `reports/latest_report.md` for the real run performed against live data
during the build of this project (sources used, exact counts, and every
field's provenance are in that file — nothing in it is fabricated; fields
that couldn't be verified are marked `NOT_AVAILABLE` or
`posting_date_status: UNVERIFIED`).

## 10. Error handling

- **Free-API connectors:** each source is wrapped individually in
  `sources/free_apis.py::fetch_all` — one source raising an exception is
  caught, logged into `search_runs.errors_json`, and does **not** stop the
  other sources or the run (spec requirement: one failed source ≠ failed
  search).
- **Missing salary / posting date / recruiter:** stored as `NOT_AVAILABLE`
  / `posting_date_status: UNVERIFIED`; never inferred or invented. Scoring
  treats missing salary as a defined mid-low tier (`not_disclosed`, worth
  4/10), not a penalty of zero and not a guess.
- **Malformed/invalid ingestion records:** `main.py ingest` validates every
  record with `sources/ai_search.py::validate_raw_job` before it touches the
  DB; invalid records are skipped and printed, not silently dropped.
- **Duplicate jobs:** handled by `dedup.py`, not treated as an error —
  merged into one canonical record with all source URLs preserved in
  `source_urls_json`.
- **Expired jobs:** `pipeline.is_expired()` only marks a job `EXPIRED` when
  it has a *verified* posting date older than 45 days — never guesses
  expiry from an unverified date.
- **Recruiter emails:** `recruiter_discovery.validate_contact()` refuses to
  store any email whose `email_source` isn't `"public"` — a hard stop
  against fabrication, not just a style guideline.

## 11. Anti-hallucination guarantees (how they're actually enforced, not just claimed)

| Rule | Enforcement |
|---|---|
| Never invent a salary | `salary_extractor.py` only returns a value when a regex actually matches text in the listing; no LLM guess, no default number. |
| Never invent a posting date | `posting_date_status` defaults to `UNVERIFIED`; recency bonus and "posted in last 24h" stat only count `VERIFIED` dates. |
| Never invent remote eligibility | `remote_verifier.py` requires an explicit textual signal; absent one, status is `UNKNOWN`, never assumed `REMOTE_INDIA_CONFIRMED`. |
| Never invent a recruiter email | `recruiter_discovery.validate_contact()` rejects any email not tagged `email_source: "public"`. |
| Never invent a job URL | `ai_search.validate_raw_job()` requires a real `http(s)://` URL for every ingested record. |

## 12. Score explainability example

```
Match Score: 90/100
Why:
  ✓ Snowflake
  ✓ Informatica (PowerCenter/IDMC)
  ✓ Oracle PL/SQL
  ✓ Airflow/Astronomer
  ✓ sql
  ✓ 16+ years experience
  ✓ Remote India Confirmed
  ✓ Lead/Senior role
Gap:
  △ Microsoft Fabric/Azure not mentioned
```
