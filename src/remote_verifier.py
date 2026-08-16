"""
Remote Verification Agent
Classifies remote status from location/description text. NEVER assumes
"Remote" == "can work from India". Falls back to UNKNOWN when unclear.
"""
import re

INDIA_HINTS = [
    r"remote\s*[-–—:]\s*india", r"india\s*[-–—:]\s*remote", r"work from india",
    r"remote \(india\)", r"based in india", r"anywhere in india",
]

GLOBAL_HINTS = [
    r"remote\s*[-–—:]\s*(anywhere|worldwide|global)", r"work from anywhere",
    r"fully remote.{0,20}(global|worldwide|anywhere)", r"remote[- ]first",
    r"global remote", r"remote, any location", r"location[- ]independent",
]

COUNTRY_RESTRICTED_HINTS = [
    r"remote\s*[-–—:]\s*(us|u\.s\.|united states)\s*only",
    r"remote\s*[-–—:]\s*(uk|u\.k\.|united kingdom)\s*only",
    r"must be (based|located) in the (us|uk|united states|united kingdom|eu|europe)",
    r"only considering candidates in\b",
    r"authoriz(ed|ation) to work in the (us|uk|united states)",
    r"remote \((us|uk|canada|europe) only\)",
    r"candidates must reside in\b",
    r"visa sponsorship is not (available|provided)",
]

HYBRID_HINTS = [r"\bhybrid\b"]

ONSITE_HINTS = [r"\bonsite\b", r"\bon-site\b", r"\bin[- ]office\b", r"\bno remote\b"]

REMOTE_GENERIC_HINTS = [r"\bremote\b", r"\bwork from home\b", r"\bwfh\b"]


def _search_any(patterns, text):
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return p
    return None


def classify_remote_status(location: str, description: str, target_country: str = "India"):
    """
    Returns dict:
      remote_status: REMOTE_INDIA_CONFIRMED | REMOTE_GLOBAL | REMOTE_COUNTRY_RESTRICTED
                      | HYBRID | ONSITE | UNKNOWN
      india_remote_eligible: YES | NO | UNKNOWN
      evidence: matched text/pattern used to decide
    """
    text = f"{location or ''} \n {description or ''}"

    hit = _search_any(INDIA_HINTS, text)
    if hit:
        return {"remote_status": "REMOTE_INDIA_CONFIRMED", "india_remote_eligible": "YES", "evidence": hit}

    hit = _search_any(GLOBAL_HINTS, text)
    if hit:
        return {"remote_status": "REMOTE_GLOBAL", "india_remote_eligible": "YES", "evidence": hit}

    hit = _search_any(COUNTRY_RESTRICTED_HINTS, text)
    if hit:
        # Only mark NO if the restriction clearly excludes India (i.e. names another
        # specific country/region without mentioning India)
        india_mentioned = re.search(r"india", text, re.IGNORECASE)
        eligible = "UNKNOWN" if india_mentioned else "NO"
        return {"remote_status": "REMOTE_COUNTRY_RESTRICTED", "india_remote_eligible": eligible, "evidence": hit}

    hit = _search_any(HYBRID_HINTS, text)
    if hit:
        return {"remote_status": "HYBRID", "india_remote_eligible": "NO", "evidence": hit}

    hit = _search_any(ONSITE_HINTS, text)
    if hit:
        return {"remote_status": "ONSITE", "india_remote_eligible": "NO", "evidence": hit}

    hit = _search_any(REMOTE_GENERIC_HINTS, text)
    if hit:
        # "Remote" mentioned but no country qualifier found anywhere -> unclear
        cleaned_hit = hit.strip("\\b")
        return {"remote_status": "UNKNOWN", "india_remote_eligible": "UNKNOWN",
                "evidence": "generic '" + cleaned_hit + "' with no location qualifier"}

    return {"remote_status": "UNKNOWN", "india_remote_eligible": "UNKNOWN", "evidence": "no remote signal found"}


def remote_score(remote_status: str, weights: dict) -> int:
    mapping = {
        "REMOTE_INDIA_CONFIRMED": weights["india_confirmed"],
        "REMOTE_GLOBAL": weights["global_remote"],
        "UNKNOWN": weights["unclear"],
        "REMOTE_COUNTRY_RESTRICTED": weights["unclear"] // 2,  # partial credit only if India not explicitly excluded
        "HYBRID": weights["hybrid"],
        "ONSITE": weights["onsite"],
    }
    return mapping.get(remote_status, weights["unclear"])
