import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import unittest
from src import skill_matcher
from src import config_loader


class TestSkillMatcher(unittest.TestCase):
    def setUp(self):
        self.cfg = config_loader.load_search_config()
        self.syn = self.cfg["skill_synonyms"]

    def test_informatica_synonyms(self):
        for text in [
            "5 years of Informatica PowerCenter experience",
            "Strong Informatica Power Center background",
            "Hands-on Informatica ETL developer",
            "Looking for an Informatica PowerCenter Developer",
            "Informatica Developer needed",
        ]:
            matches = skill_matcher.find_matched_skill_groups(text, self.syn)
            self.assertIn("informatica_powercenter", matches, text)

    def test_plsql_synonyms(self):
        for text in ["Oracle PL/SQL required", "Oracle PL SQL developer", "Strong PLSQL skills", "Oracle SQL/PLSQL"]:
            matches = skill_matcher.find_matched_skill_groups(text, self.syn)
            self.assertIn("oracle_plsql", matches, text)

    def test_airflow_synonyms(self):
        for text in ["Apache Airflow pipelines", "Experience with Airflow", "Astro Airflow orchestration", "Astronomer platform"]:
            matches = skill_matcher.find_matched_skill_groups(text, self.syn)
            self.assertIn("airflow", matches, text)

    def test_fabric_synonyms(self):
        for text in ["Microsoft Fabric experience", "Fabric Data Engineering", "Fabric Lakehouse design", "Fabric Data Factory pipelines"]:
            matches = skill_matcher.find_matched_skill_groups(text, self.syn)
            self.assertIn("ms_fabric", matches, text)

    def test_no_false_positive(self):
        text = "We need a Java backend engineer with Kubernetes experience"
        matches = skill_matcher.find_matched_skill_groups(text, self.syn)
        self.assertNotIn("snowflake", matches)
        self.assertNotIn("informatica_powercenter", matches)

    def test_seniority_classification(self):
        self.assertEqual(skill_matcher.classify_seniority("Data Engineering Manager"), "manager_architect")
        self.assertEqual(skill_matcher.classify_seniority("Senior Data Engineer"), "lead_senior")
        self.assertEqual(skill_matcher.classify_seniority("Data Engineer II"), "mid_level")
        self.assertEqual(skill_matcher.classify_seniority("Junior Data Engineer"), "junior")

    def test_experience_bucket(self):
        w = self.cfg["scoring"]["experience"]
        self.assertEqual(skill_matcher.experience_bucket_score(16, w), w["15_plus"])
        self.assertEqual(skill_matcher.experience_bucket_score(12, w), w["10_14"])
        self.assertEqual(skill_matcher.experience_bucket_score(8, w), w["7_9"])
        self.assertEqual(skill_matcher.experience_bucket_score(3, w), w["below_7"])


if __name__ == "__main__":
    unittest.main()
