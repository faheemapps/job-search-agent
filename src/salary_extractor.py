"""
Salary Extraction Agent
Extracts salary figures from text using regex heuristics only — never
invents a number. If nothing is found, salary_tier = 'not_disclosed'.
"""
import re

CURRENCY_SYMBOLS = {
    "$": "USD", "₹": "INR", "£": "GBP", "€": "EUR", "AED": "AED",
}

# Patterns like "$120,000 - $150,000", "INR 40,00,000 - 55,00,000",
# "₹40L - ₹55L", "40-55 LPA", "AED 25,000/month"
PATTERNS = [
    # symbol ranges: $120,000 - $150,000
    re.compile(
        r"(?P<sym>[$₹£€])\s?(?P<low>[\d,]+(?:\.\d+)?)\s*(?P<lowk>[kK])?\s*[-–to]{1,4}\s?(?P<sym2>[$₹£€])?\s?(?P<high>[\d,]+(?:\.\d+)?)\s*(?P<highk>[kK])?"
    ),
    # single value: $150,000
    re.compile(r"(?P<sym>[$₹£€])\s?(?P<low>[\d,]+(?:\.\d+)?)\s*(?P<lowk>[kK])?"),
    # LPA ranges: 40-55 LPA / 40 to 55 LPA
    re.compile(r"(?P<low>\d{1,3})\s*[-–to]{1,4}\s*(?P<high>\d{1,3})\s*LPA", re.IGNORECASE),
    re.compile(r"(?P<low>\d{1,3})\s*LPA", re.IGNORECASE),
    # explicit currency code: AED 25,000 - 30,000 / month
    re.compile(
        r"(?P<code>AED|USD|GBP|EUR|INR)\s?(?P<low>[\d,]+)\s*[-–to]{1,4}\s?(?P<high>[\d,]+)?", re.IGNORECASE
    ),
]


def _to_number(raw, is_k):
    val = float(raw.replace(",", ""))
    if is_k:
        val *= 1000
    return val


def extract_salary(text: str):
    """
    Returns dict: {salary_raw, salary_min, salary_max, currency} or None if
    nothing found. Values are best-effort annualized guesses based on the
    literal text; monthly figures are converted to annual (x12) only when
    the text explicitly says "/month" or "per month".
    """
    if not text:
        return None

    monthly = bool(re.search(r"/\s*month|per month|monthly", text, re.IGNORECASE))
    lpa = bool(re.search(r"LPA", text, re.IGNORECASE))

    for pat in PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        gd = m.groupdict()
        currency = None
        if gd.get("sym"):
            currency = CURRENCY_SYMBOLS.get(gd["sym"])
        elif gd.get("code"):
            currency = gd["code"].upper()
        elif lpa:
            currency = "INR"

        if not currency:
            continue

        try:
            low = _to_number(gd["low"], bool(gd.get("lowk")))
        except (TypeError, ValueError, KeyError):
            continue
        high = None
        if gd.get("high"):
            try:
                high = _to_number(gd["high"], bool(gd.get("highk")))
            except (TypeError, ValueError):
                high = None

        if lpa:
            low *= 100000  # lakhs -> INR
            if high:
                high *= 100000
        if monthly:
            low *= 12
            if high:
                high *= 12

        return {
            "salary_raw": m.group(0),
            "salary_min": low,
            "salary_max": high or low,
            "currency": currency,
        }
    return None


def classify_salary_tier(salary_min, salary_max, currency, thresholds: dict):
    if salary_min is None or not currency or currency not in thresholds:
        return "not_disclosed"
    t = thresholds[currency]
    value = salary_max or salary_min
    if value >= t["very_high"]:
        return "very_high"
    if value >= t["high"]:
        return "high"
    if value >= t["average"]:
        return "average"
    return "low"


def salary_score(tier: str, weights: dict) -> int:
    return weights.get(tier, weights["not_disclosed"])


def meets_minimum_target(salary_min, salary_max, currency, minimum_target: dict):
    """minimum_target e.g. {'INR': 4000000}. Returns True/False/None(unknown)."""
    if not currency or currency not in minimum_target:
        return None
    if salary_min is None:
        return None
    value = salary_max or salary_min
    return value >= minimum_target[currency]
