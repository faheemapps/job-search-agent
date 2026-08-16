"""
Skill Matching Agent
Semantic-ish matching using synonym groups defined in job_search_config.yaml,
plus fuzzy fallback (difflib) for near-miss spelling/phrasing variants that
aren't in the explicit synonym list.
"""
import re
import difflib


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9/+.\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_matched_skill_groups(text: str, synonym_groups: dict, fuzzy_threshold: float = 0.90):
    """
    Returns dict: {group_name: [matched_variant, ...]} for every synonym
    group that has at least one hit in `text`.
    """
    norm_text = _normalize(text or "")
    matches = {}
    for group_name, variants in synonym_groups.items():
        hits = []
        for variant in variants:
            v = _normalize(variant)
            if not v:
                continue
            # direct substring match (word-boundary aware where possible)
            pattern = re.escape(v)
            if re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", norm_text):
                hits.append(variant)
                continue
            # fuzzy fallback: scan tokens/windows for close matches (handles
            # things like "PL SQL" vs "PL/SQL" vs minor typos)
            tokens = norm_text.split()
            v_tokens = v.split()
            window = len(v_tokens)
            if window == 0:
                continue
            for i in range(0, max(1, len(tokens) - window + 1)):
                chunk = " ".join(tokens[i:i + window])
                ratio = difflib.SequenceMatcher(None, chunk, v).ratio()
                if ratio >= fuzzy_threshold:
                    hits.append(variant)
                    break
        if hits:
            matches[group_name] = sorted(set(hits))
    return matches


def core_technology_score(matched_groups: dict, weights: dict) -> tuple:
    """
    weights: scoring.core_technology from config
      snowflake, informatica, oracle_plsql, ms_fabric_azure, airflow, python_sql_etl_dw
    Returns (score, explanation_list)
    """
    score = 0
    why = []
    gaps = []

    if "snowflake" in matched_groups:
        score += weights["snowflake"]
        why.append("Snowflake")
    else:
        gaps.append("Snowflake")

    if "informatica_powercenter" in matched_groups or "informatica_idmc" in matched_groups:
        score += weights["informatica"]
        why.append("Informatica (PowerCenter/IDMC)")
    else:
        gaps.append("Informatica PowerCenter/IDMC")

    if "oracle_plsql" in matched_groups:
        score += weights["oracle_plsql"]
        why.append("Oracle PL/SQL")
    else:
        gaps.append("Oracle PL/SQL")

    if "ms_fabric" in matched_groups or "azure" in matched_groups or "adls" in matched_groups:
        score += weights["ms_fabric_azure"]
        why.append("Microsoft Fabric/Azure")
    else:
        gaps.append("Microsoft Fabric/Azure")

    if "airflow" in matched_groups:
        score += weights["airflow"]
        why.append("Airflow/Astronomer")
    else:
        gaps.append("Airflow")

    generic_hit = any(g in matched_groups for g in ("python", "sql", "etl", "data_warehouse"))
    if generic_hit:
        score += weights["python_sql_etl_dw"]
        found = [g for g in ("python", "sql", "etl", "data_warehouse") if g in matched_groups]
        why.append("/".join(found))
    else:
        gaps.append("Python/SQL/ETL/DW")

    return score, why, gaps


SENIORITY_PATTERNS = {
    "manager_architect": [
        r"\bmanager\b", r"\barchitect\b", r"\bhead of\b", r"\bdirector\b", r"\bprincipal\b",
    ],
    "lead_senior": [
        r"\blead\b", r"\bsenior\b", r"\bsr\.?\b", r"\bstaff\b",
    ],
    "mid_level": [
        r"\bmid[- ]level\b", r"\bii\b", r"\biii\b", r"\bassociate\b",
    ],
    "junior": [
        r"\bjunior\b", r"\bjr\.?\b", r"\bentry[- ]level\b", r"\bgraduate\b", r"\bintern\b",
    ],
}


def classify_seniority(job_title: str, job_description: str = "") -> str:
    text = _normalize(f"{job_title} {job_description[:500]}")
    for level in ("manager_architect", "lead_senior", "mid_level", "junior"):
        for pat in SENIORITY_PATTERNS[level]:
            if re.search(pat, text):
                return level
    return "mid_level"  # default assumption when unclear, conservative middle score


def seniority_score(level: str, weights: dict) -> int:
    return weights.get(level, weights["mid_level"])


EXPERIENCE_RE = re.compile(
    r"(\d{1,2})\s*(?:\+|-|to)?\s*(\d{1,2})?\s*(?:years|yrs)", re.IGNORECASE
)


def extract_required_experience(text: str):
    """Returns a string like '10+ years' or None if not stated."""
    if not text:
        return None
    m = EXPERIENCE_RE.search(text)
    if not m:
        return None
    low = m.group(1)
    high = m.group(2)
    if high:
        return f"{low}-{high} years"
    return f"{low}+ years"


def experience_bucket_score(candidate_years: int, weights: dict) -> int:
    if candidate_years >= 15:
        return weights["15_plus"]
    if candidate_years >= 10:
        return weights["10_14"]
    if candidate_years >= 7:
        return weights["7_9"]
    return weights["below_7"]
