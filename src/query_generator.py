"""
Search Query Generator
Seeds from job_search_config.yaml -> seed_queries, then expands dynamically
using terminology discovered in previously matched job titles (persisted in
data/discovered_terms.json).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_discovered_terms(path=None):
    path = Path(path) if path else ROOT / "data" / "discovered_terms.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_discovered_terms(terms, path=None):
    path = Path(path) if path else ROOT / "data" / "discovered_terms.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(sorted(set(terms)), f, indent=2)


TITLE_TERM_PATTERNS = [
    r"\bsnowflake [a-z]+ (developer|engineer|architect)\b",
    r"\betl [a-z]+ (developer|engineer|architect|lead)\b",
    r"\bdata (warehouse|platform) [a-z]+\b",
    r"\binformatica [a-z]+ (developer|engineer)\b",
]


def discover_terms_from_titles(job_titles: list) -> list:
    """Extract recurring multi-word technical phrases from a batch of job
    titles so future runs can search them directly (spec section 4)."""
    found = []
    for title in job_titles:
        t = title.lower()
        for pat in TITLE_TERM_PATTERNS:
            m = re.search(pat, t)
            if m:
                found.append(m.group(0).strip())
    return found


def generate_queries(seed_queries: list, discovered_terms: list, max_queries=None):
    all_queries = list(dict.fromkeys(seed_queries + discovered_terms))  # dedupe, keep order
    if max_queries:
        return all_queries[:max_queries]
    return all_queries
