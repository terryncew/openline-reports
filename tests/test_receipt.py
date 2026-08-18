import unittest
from openline_reports.receipt import make_handoff

class ReceiptTests(unittest.TestCase):
    def base(self):
        return {
            "investigation_id": "x",
            "title": "t",
            "question": "q",
            "initial_hypothesis": "h",
            "sources": [],
            "claims": [],
            "objections": [],
            "discovery_delta": "",
            "result_summary": "",
            "disposition": "kill",
            "disposition_reason": "nothing here",
            "reopened_from_hash": "",
        }

    def test_handoff_binds_investigation(self):
        inv = self.base()
        r1 = make_handoff(inv)
        inv["title"] = "changed"
        r2 = make_handoff(inv)
        self.assertNotEqual(r1["investigation_hash"], r2["investigation_hash"])

    def test_handoff_requires_disposition(self):
        inv = self.base()
        inv["disposition"] = None
        with self.assertRaises(ValueError):
            make_handoff(inv)

    def test_receipt_timestamp_is_not_claimed_deterministic(self):
        inv = self.base()
        r = make_handoff(inv)
        self.assertIn("created_at", r)
        self.assertEqual(r["authority"], "research_handoff_only")

if __name__ == "__main__":
    unittest.main()
