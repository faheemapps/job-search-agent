import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import unittest
from src import remote_verifier as rv


class TestRemoteVerifier(unittest.TestCase):
    def test_india_confirmed(self):
        r = rv.classify_remote_status("Remote - India", "")
        self.assertEqual(r["remote_status"], "REMOTE_INDIA_CONFIRMED")
        self.assertEqual(r["india_remote_eligible"], "YES")

    def test_global_remote(self):
        r = rv.classify_remote_status("Remote - Anywhere", "")
        self.assertEqual(r["remote_status"], "REMOTE_GLOBAL")
        self.assertEqual(r["india_remote_eligible"], "YES")

    def test_country_restricted(self):
        r = rv.classify_remote_status("Remote - United States only", "")
        self.assertEqual(r["remote_status"], "REMOTE_COUNTRY_RESTRICTED")
        self.assertEqual(r["india_remote_eligible"], "NO")

    def test_hybrid(self):
        r = rv.classify_remote_status("Hybrid - NYC", "")
        self.assertEqual(r["remote_status"], "HYBRID")

    def test_onsite(self):
        r = rv.classify_remote_status("Onsite - Bangalore", "")
        self.assertEqual(r["remote_status"], "ONSITE")

    def test_unknown_generic_remote(self):
        r = rv.classify_remote_status("Remote", "")
        self.assertEqual(r["remote_status"], "UNKNOWN")
        self.assertEqual(r["india_remote_eligible"], "UNKNOWN")

    def test_unknown_no_signal(self):
        r = rv.classify_remote_status("", "")
        self.assertEqual(r["remote_status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
