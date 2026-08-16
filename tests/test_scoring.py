import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import unittest
from src import scoring, config_loader


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.profile = config_loader.load_profile()
        self.cfg = config_loader.load_search_config()

    def test_strong_match_scores_high(self):
        job = {
            "job_title": "Data Engineering Manager - Snowflake",
            "job_description": (
                "We need a Data Engineering Manager with Snowflake, Informatica PowerCenter, "
                "Oracle PL/SQL, Microsoft Fabric, Airflow and Python. 15+ years experience required. "
                "Remote - India. Salary INR 55,00,000 - 65,00,000 per annum."
            ),
            "location": "Remote - India",
            "company_name": "TestCo",
            "job_url": "https://example.com/job/1",
            "primary_source": "LinkedIn",
        }
        scored = scoring.score_job(job, self.profile, self.cfg)
        self.assertGreaterEqual(scored["match_score"], 85)
        self.assertEqual(scored["remote_status"], "REMOTE_INDIA_CONFIRMED")
        self.assertEqual(scored["salary_tier"], "very_high")

    def test_weak_match_scores_low(self):
        job = {
            "job_title": "Junior Marketing Analyst",
            "job_description": "Excel and PowerPoint skills needed. Onsite in New York.",
            "location": "Onsite - New York",
            "company_name": "TestCo2",
            "job_url": "https://example.com/job/2",
            "primary_source": "Indeed",
        }
        scored = scoring.score_job(job, self.profile, self.cfg)
        self.assertLess(scored["match_score"], 30)

    def test_score_capped_0_100(self):
        job = {
            "job_title": "Data Architect Manager Lead Senior Snowflake",
            "job_description": "Snowflake Informatica PowerCenter Oracle PL/SQL Microsoft Fabric Airflow Python SQL ETL",
            "location": "Remote - Anywhere",
            "company_name": "TestCo3",
            "job_url": "https://example.com/job/3",
            "primary_source": "Dice",
            "salary_raw": "$300,000 - $400,000",
        }
        scored = scoring.score_job(job, self.profile, self.cfg)
        self.assertLessEqual(scored["match_score"], 100)


if __name__ == "__main__":
    unittest.main()
