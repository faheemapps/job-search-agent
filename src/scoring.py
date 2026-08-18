"""
Scoring + Ranking Engine
Combines: core technology (50) + seniority (15) + experience (10) +
remote (15) + salary (10) = 0-100 base match_score, matching the Top-20
report's "Match Score: X/100" display. Bonus points (recency + skill-combo +
india-remote-high-salary) are added separately as `rank_score` and used only
to order results — they don't inflate the displayed /100 score.
"""
from datetime import datetime, timezone

from . import skill_matcher, remote_verifier, salary_extractor


def recency_tier(posting_date_iso, posting_date_status, tiers: dict):
    if posting_date_status != "VERIFIED" or not posting_date_iso:
        return "unverified_or_older"
    try:
        dt = datetime.fromisoformat(str(posting_date_iso).replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return "unverified_or_older"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    if hours <= tiers["tier1_hours"]:
        return "tier1_24h"
    if hours <= tiers["tier2_hours"]:
        return "tier2_3d"
    if hours <= tiers["tier3_hours"]:
        return "tier3_7d"
    if hours <= tiers["tier4_hours"]:
        return "tier4_14d"
    return "unverified_or_older"


def score_job(job: dict, profile: dict, search_cfg: dict):
    """
    job: normalized job dict (job_title, job_description, location, salary_raw,
         posting_date, posting_date_status, ...)
    profile: candidate_profile.yaml dict
    search_cfg: job_search_config.yaml dict

    Returns the job dict, mutated in place with:
      skills, remote_status, india_remote_eligible, salary fields,
      match_score, rank_score, score_breakdown
    """
    weights = search_cfg["scoring"]
    text_blob = f"{job.get('job_title','')} \n {job.get('job_description','')}"

    # --- Skill matching -----------------------------------------------
    matched_groups = skill_matcher.find_matched_skill_groups(text_blob, search_cfg["skill_synonyms"])
    tech_score, tech_why, tech_gaps = skill_matcher.core_technology_score(matched_groups, weights["core_technology"])
    job["skills"] = sorted(matched_groups.keys())

    # --- Seniority -------------------------------------------------------
    level = skill_matcher.classify_seniority(job.get("job_title", ""), job.get("job_description", ""))
    sen_score = skill_matcher.seniority_score(level, weights["seniority"])

    # --- Experience --------------------------------------------------------
    exp_score = skill_matcher.experience_bucket_score(profile["experience_years"], weights["experience"])
    if not job.get("experience_required"):
        job["experience_required"] = skill_matcher.extract_required_experience(job.get("job_description", "")) or "NOT_AVAILABLE"

    # --- Remote verification ------------------------------------------------
    remote_info = remote_verifier.classify_remote_status(job.get("location", ""), job.get("job_description", ""))
    job["remote_status"] = remote_info["remote_status"]
    job["remote_status_evidence"] = remote_info["evidence"]
    job["india_remote_eligible"] = remote_info["india_remote_eligible"]
    rem_score = remote_verifier.remote_score(remote_info["remote_status"], weights["remote"])

    # --- Salary --------------------------------------------------------------
    if not job.get("salary_min"):
        extracted = salary_extractor.extract_salary(f"{job.get('salary_raw','')} {job.get('job_description','')}")
        if extracted:
            job.update(extracted)
    tier = salary_extractor.classify_salary_tier(
        job.get("salary_min"), job.get("salary_max"), job.get("currency"), search_cfg["salary_thresholds"]
    )
    job["salary_tier"] = tier
    sal_score = salary_extractor.salary_score(tier, weights["salary"])

    base_score = tech_score + sen_score + exp_score + rem_score + sal_score
    base_score = max(0, min(100, base_score))

    # --- Bonuses (ranking only) ------------------------------------------------
    bonuses = weights["bonuses"]
    bonus_total = 0
    bonus_why = []

    has_snowflake = "snowflake" in matched_groups
    has_informatica = "informatica_powercenter" in matched_groups or "informatica_idmc" in matched_groups
    has_plsql = "oracle_plsql" in matched_groups
    has_fabric = "ms_fabric" in matched_groups
    has_airflow = "airflow" in matched_groups

    if has_snowflake and has_informatica and has_plsql:
        bonus_total += bonuses["snowflake_informatica_plsql"]
        bonus_why.append("Snowflake+Informatica+PL/SQL combo")

    if has_snowflake and has_fabric and has_airflow:
        bonus_total += bonuses["snowflake_fabric_airflow"]
        bonus_why.append("Snowflake+Fabric+Airflow combo")

    meets_target = salary_extractor.meets_minimum_target(
        job.get("salary_min"), job.get("salary_max"), job.get("currency"), profile["minimum_target_salary"]
    )
    if remote_info["remote_status"] in ("REMOTE_INDIA_CONFIRMED", "REMOTE_GLOBAL") and meets_target:
        bonus_total += bonuses["india_remote_high_salary"]
        bonus_why.append("Remote-from-India + salary meets target")

    r_tier = recency_tier(job.get("posting_date"), job.get("posting_date_status", "UNVERIFIED"), search_cfg["recency_tiers"])
    recency_bonus = bonuses["recency"][r_tier]
    bonus_total += recency_bonus
    job["recency_tier"] = r_tier

    job["match_score"] = round(base_score)
    job["rank_score"] = round(base_score + bonus_total, 2)
    job["score_breakdown"] = {
        "core_technology": {"score": tech_score, "max": 50, "matched": tech_why, "gaps": tech_gaps},
        "seniority": {"score": sen_score, "max": 15, "level": level},
        "experience": {"score": exp_score, "max": 10, "years": profile["experience_years"]},
        "remote": {"score": rem_score, "max": 15, "status": remote_info["remote_status"], "evidence": remote_info["evidence"]},
        "salary": {"score": sal_score, "max": 10, "tier": tier},
        "bonuses": {"total": bonus_total, "reasons": bonus_why, "recency_tier": r_tier},
    }
    return job


def explain(job: dict) -> str:
    b = job["score_breakdown"]
    lines = [f"Match Score: {job['match_score']}/100", "Why:"]
    for skill in b["core_technology"]["matched"]:
        lines.append(f"  ✓ {skill}")
    lines.append(f"  ✓ {job['score_breakdown']['experience']['years']}+ years experience")
    if b["remote"]["status"] in ("REMOTE_INDIA_CONFIRMED", "REMOTE_GLOBAL"):
        lines.append(f"  ✓ {b['remote']['status'].replace('_', ' ').title()}")
    if b["seniority"]["level"] in ("manager_architect", "lead_senior"):
        lines.append(f"  ✓ {b['seniority']['level'].replace('_', '/').title()} role")
    if b["core_technology"]["gaps"]:
        lines.append("Gap:")
        for gap in b["core_technology"]["gaps"]:
            lines.append(f"  △ {gap} not mentioned")
    return "\n".join(lines)
