"""
Deduplication Engine
The same job frequently appears on multiple sources (LinkedIn, Indeed,
Naukri, company career page, Google). This module collapses duplicates into
one canonical job record and merges all discovered URLs.
"""
import re
import difflib
import hashlib


def normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    # strip common noise tokens that don't affect role identity
    noise = ["remote", "hybrid", "onsite", "urgent", "hiring", "immediate joiner",
             "job", "opening", "new", "req", "requisition"]
    for n in noise:
        t = re.sub(rf"\b{n}\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_company(name: str) -> str:
    n = name.lower()
    n = re.sub(r"[^a-z0-9\s]", " ", n)
    for suffix in ["inc", "llc", "ltd", "limited", "pvt", "private", "corp",
                   "corporation", "gmbh", "plc", "co"]:
        n = re.sub(rf"\b{suffix}\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def normalize_location(loc: str) -> str:
    if not loc:
        return ""
    l = loc.lower()
    l = re.sub(r"[^a-z0-9\s]", " ", l)
    l = re.sub(r"\s+", " ", l).strip()
    return l


def compute_job_uid(company: str, title: str, location: str) -> str:
    """Stable identity hash independent of source — used as the DB unique key
    for a *specific* posting instance. Near-duplicate detection (different
    hash, same job) is handled separately by find_duplicate()."""
    key = f"{normalize_company(company)}|{normalize_title(title)}|{normalize_location(location)}"
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


def find_duplicate(new_job: dict, existing_jobs: list, title_thresh=0.82, desc_thresh=0.80):
    """
    existing_jobs: list of normalized job dicts already collected in this run
    (or loaded from DB) to compare against.
    Returns the matching existing job dict, or None.
    """
    nc = normalize_company(new_job["company_name"])
    nt = normalize_title(new_job["job_title"])
    for ex in existing_jobs:
        ec = normalize_company(ex["company_name"])
        if nc != ec:
            continue
        et = normalize_title(ex["job_title"])
        title_sim = similarity(nt, et)
        if title_sim >= title_thresh:
            return ex
        # same company, different-looking title: fall back to description similarity
        desc_sim = similarity(
            (new_job.get("job_description") or "")[:1000],
            (ex.get("job_description") or "")[:1000],
        )
        if desc_sim >= desc_thresh and title_sim >= 0.55:
            return ex
    return None


def merge_into_canonical(canonical: dict, duplicate: dict, source_priority_order: list):
    """
    Merge `duplicate` into `canonical`, preferring the higher-priority
    source's URL/fields when both provide a value, per source_priority_order
    (lower index = more trusted).
    """
    def rank(source_name):
        try:
            return source_priority_order.index(source_name)
        except ValueError:
            return len(source_priority_order)

    canon_sources = {u["url"]: u for u in canonical.get("source_urls", [])}
    for u in duplicate.get("source_urls", []):
        canon_sources[u["url"]] = u
    canonical["source_urls"] = list(canon_sources.values())

    if rank(duplicate.get("primary_source")) < rank(canonical.get("primary_source")):
        # duplicate came from a more trusted source -> promote its canonical fields
        for field in ("job_url", "company_url", "job_description", "salary_raw",
                      "salary_min", "salary_max", "currency", "posting_date",
                      "posting_date_status", "primary_source"):
            if duplicate.get(field):
                canonical[field] = duplicate[field]
        canonical["canonical_source"] = duplicate.get("primary_source")
    else:
        # fill any gaps in canonical from the duplicate without overwriting
        for field in ("salary_raw", "salary_min", "salary_max", "currency",
                      "posting_date", "job_description"):
            if not canonical.get(field) and duplicate.get(field):
                canonical[field] = duplicate[field]

    return canonical
