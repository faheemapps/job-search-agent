import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import unittest
from src import dedup


class TestDedup(unittest.TestCase):
    def test_same_job_different_sources_dedupes(self):
        j1 = {
            "company_name": "Acme Corp", "job_title": "Senior Data Engineer - Snowflake",
            "location": "Remote", "job_description": "Snowflake ETL Informatica PL/SQL role",
            "primary_source": "LinkedIn", "job_url": "https://linkedin.com/jobs/1",
            "source_urls": [{"source": "LinkedIn", "url": "https://linkedin.com/jobs/1"}],
        }
        j2 = {
            "company_name": "Acme Corp Inc", "job_title": "Senior Data Engineer – Snowflake",
            "location": "Remote", "job_description": "Snowflake ETL Informatica PL/SQL role",
            "primary_source": "Indeed", "job_url": "https://indeed.com/jobs/2",
            "source_urls": [{"source": "Indeed", "url": "https://indeed.com/jobs/2"}],
        }
        dup = dedup.find_duplicate(j2, [j1])
        self.assertIsNotNone(dup)

    def test_different_jobs_not_deduped(self):
        j1 = {
            "company_name": "Acme Corp", "job_title": "Senior Data Engineer",
            "location": "Remote", "job_description": "Snowflake role",
        }
        j2 = {
            "company_name": "Beta Inc", "job_title": "Data Analyst",
            "location": "Onsite", "job_description": "Excel and Tableau reporting",
        }
        dup = dedup.find_duplicate(j2, [j1])
        self.assertIsNone(dup)

    def test_merge_prefers_higher_priority_source(self):
        canonical = {
            "primary_source": "Indeed", "job_url": "https://indeed.com/1",
            "source_urls": [{"source": "Indeed", "url": "https://indeed.com/1"}],
        }
        duplicate = {
            "primary_source": "CompanyCareerPage", "job_url": "https://acme.com/careers/1",
            "source_urls": [{"source": "CompanyCareerPage", "url": "https://acme.com/careers/1"}],
        }
        priority = ["CompanyCareerPage", "LinkedIn", "Indeed"]
        merged = dedup.merge_into_canonical(canonical, duplicate, priority)
        self.assertEqual(merged["job_url"], "https://acme.com/careers/1")
        self.assertEqual(len(merged["source_urls"]), 2)


if __name__ == "__main__":
    unittest.main()
