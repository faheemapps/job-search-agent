"""
Alert Engine — flags exceptional jobs per job_search_config.yaml -> alerts.rules
"""


def evaluate_alerts(job: dict, profile: dict):
    """Returns list of alert names triggered for this job."""
    triggered = []
    score = job.get("match_score", 0)
    india_remote = job.get("remote_status") == "REMOTE_INDIA_CONFIRMED"

    if score >= 85 and india_remote:
        triggered.append("excellent_india_remote")

    if score >= 90:
        triggered.append("exceptional_score")

    breakdown = job.get("score_breakdown", {})
    matched = breakdown.get("core_technology", {}).get("matched", [])
    has_core_stack = (
        any("Snowflake" in m for m in matched)
        and any("Informatica" in m for m in matched)
        and any("PL/SQL" in m for m in matched)
    )
    from .salary_extractor import meets_minimum_target
    meets_target = meets_minimum_target(
        job.get("salary_min"), job.get("salary_max"), job.get("currency"), profile["minimum_target_salary"]
    )
    if has_core_stack and meets_target:
        triggered.append("core_stack_high_salary")

    return triggered
