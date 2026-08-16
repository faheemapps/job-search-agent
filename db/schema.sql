-- =============================================================================
-- JOB SEARCH AGENT — SQLite schema
-- =============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS candidate_profile (
    id              INTEGER PRIMARY KEY CHECK (id = 1),   -- single-row table
    profile_yaml    TEXT NOT NULL,                        -- full YAML snapshot used for this DB
    loaded_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS companies (
    company_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    website         TEXT,
    careers_url     TEXT,
    industry        TEXT,
    created_at      TEXT NOT NULL,
    UNIQUE(normalized_name)
);

CREATE TABLE IF NOT EXISTS job_sources (
    source_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    type            TEXT NOT NULL,           -- api | mcp_tool | ai_search
    priority        INTEGER NOT NULL,
    enabled         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    job_uid                 TEXT NOT NULL UNIQUE,     -- stable hash used for dedup identity
    job_title               TEXT NOT NULL,
    normalized_title        TEXT NOT NULL,
    company_id              INTEGER REFERENCES companies(company_id),
    company_name            TEXT NOT NULL,
    location                TEXT,
    remote_status            TEXT,                     -- REMOTE_INDIA_CONFIRMED | REMOTE_GLOBAL | REMOTE_COUNTRY_RESTRICTED | HYBRID | ONSITE | UNKNOWN
    remote_status_evidence   TEXT,                      -- text snippet used to classify
    india_remote_eligible    TEXT,                      -- YES | NO | UNKNOWN
    posting_date             TEXT,                       -- ISO date if known
    posting_date_status      TEXT NOT NULL DEFAULT 'UNVERIFIED',  -- VERIFIED | UNVERIFIED
    experience_required      TEXT,
    salary_raw                TEXT,
    salary_min                REAL,
    salary_max                REAL,
    currency                  TEXT,
    salary_tier                TEXT,                     -- very_high|high|average|low|not_disclosed
    salary_source_url          TEXT,
    skills_json                 TEXT,                     -- JSON array of matched skill groups
    job_description             TEXT,
    job_url                     TEXT NOT NULL,
    company_url                  TEXT,
    canonical_source              TEXT,                    -- which source's URL was chosen as canonical
    source_urls_json               TEXT,                    -- JSON array of {source, url}
    primary_source                  TEXT NOT NULL,
    recruiter_name                   TEXT DEFAULT 'NOT_AVAILABLE',
    recruiter_title                  TEXT DEFAULT 'NOT_AVAILABLE',
    recruiter_linkedin                TEXT DEFAULT 'NOT_AVAILABLE',
    recruiter_email                    TEXT DEFAULT 'NOT_AVAILABLE',
    email_source                       TEXT,                  -- 'public' when a public source was found
    match_score                         INTEGER DEFAULT 0,      -- 0-100 base rubric score
    rank_score                          REAL DEFAULT 0,         -- base + bonuses, used for ORDER BY only
    score_breakdown_json                 TEXT,
    status                                TEXT NOT NULL DEFAULT 'NEW', -- NEW|SEEN|SHORTLISTED|APPLIED|EXPIRED|REJECTED
    first_seen                            TEXT NOT NULL,
    last_seen                             TEXT NOT NULL,
    last_verified                         TEXT,
    search_run_id                         INTEGER REFERENCES search_runs(run_id)
);

CREATE TABLE IF NOT EXISTS contacts (
    contact_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER REFERENCES jobs(job_id),
    name            TEXT,
    title           TEXT,
    linkedin_url    TEXT,
    email           TEXT,
    email_source    TEXT,           -- 'public' only; never fabricated
    discovered_via  TEXT,           -- search query used
    discovered_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    application_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id           INTEGER REFERENCES jobs(job_id),
    company          TEXT,
    role             TEXT,
    job_url          TEXT,
    date_found       TEXT,
    date_applied     TEXT,
    status           TEXT NOT NULL DEFAULT 'NOT_APPLIED', -- NOT_APPLIED|APPLY|APPLIED|INTERVIEW|REJECTED|OFFER|CLOSED
    recruiter        TEXT,
    recruiter_contact TEXT,
    resume_version   TEXT,
    notes            TEXT,
    updated_at       TEXT
);

CREATE TABLE IF NOT EXISTS search_runs (
    run_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    queries_used_json TEXT,
    sources_used_json TEXT,
    new_jobs_found    INTEGER DEFAULT 0,
    total_jobs_seen   INTEGER DEFAULT 0,
    strong_matches    INTEGER DEFAULT 0,
    excellent_matches INTEGER DEFAULT 0,
    posted_last_24h   INTEGER DEFAULT 0,
    india_remote_confirmed INTEGER DEFAULT 0,
    high_paying       INTEGER DEFAULT 0,
    errors_json       TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(job_title);
CREATE INDEX IF NOT EXISTS idx_jobs_posting_date ON jobs(posting_date);
CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(job_url);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score);
