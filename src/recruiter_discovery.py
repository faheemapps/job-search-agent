"""
Recruiter Discovery Agent
Publicly-available-information only. Never fabricates a name, title, or
email. Designed to be driven by a Claude session's WebSearch tool (recruiter
identity lookups have no public API); this module supplies the query
templates and a strict validator so fabricated-looking data can never reach
the database.
"""
import re

QUERY_TEMPLATES = [
    '"{company}" "{title}" recruiter',
    '"{company}" "{title}" "talent acquisition"',
    '"{company}" "{title}" "hiring manager"',
    '"{company}" careers "talent acquisition" site:linkedin.com/in',
]


def build_queries(company: str, job_title: str) -> list:
    return [t.format(company=company, title=job_title) for t in QUERY_TEMPLATES]


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def validate_contact(contact: dict) -> list:
    """Returns validation errors. A contact is only accepted if it came from
    a real, cited public source (search result / public profile), never
    guessed or pattern-generated (e.g. first.last@company.com guesses)."""
    errors = []
    if contact.get("email") and contact.get("email") != "NOT_AVAILABLE":
        if not EMAIL_RE.match(contact["email"]):
            errors.append("email does not look like a valid address")
        if contact.get("email_source") != "public":
            errors.append("email present but email_source is not 'public' — refusing to store (anti-fabrication rule)")
    if contact.get("linkedin_url") and "linkedin.com" not in contact["linkedin_url"]:
        errors.append("linkedin_url does not look like a LinkedIn URL")
    return errors


def empty_contact() -> dict:
    return {
        "name": "NOT_AVAILABLE",
        "title": "NOT_AVAILABLE",
        "linkedin_url": "NOT_AVAILABLE",
        "email": "NOT_AVAILABLE",
        "email_source": None,
    }
