import json
import tempfile
import unittest
from pathlib import Path
from openline_reports.model import Investigation, SourceRef, Claim
from openline_reports.io import save, load
from openline_reports.canonical import sha256_obj
from openline_reports.cli import _verify_reopen_lineage

class LineageTests(unittest.TestCase):
    def prior(self):
        return Investigation(
            "x","t","q","h",
            sources=[SourceRef("s1","src","loc")],
            claims=[Claim("c1","claim","supported",["s1"])],
            discovery_delta="d",
            result_summary="r",
            disposition="candidate",
        )

    def test_matching_prior_hash_passes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"prior.json"
            prior = self.prior()
            save(prior,p)
            current = self.prior()
            current.disposition = "pivot"
            current.reopened_from_hash = sha256_obj(prior.to_dict())
            self.assertEqual(_verify_reopen_lineage(current, str(p)), [])

    def test_wrong_prior_hash_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/"prior.json"
            prior = self.prior()
            save(prior,p)
            current = self.prior()
            current.disposition = "pivot"
            current.reopened_from_hash = "0"*64
            self.assertIn("reopened_from_hash_mismatch", _verify_reopen_lineage(current, str(p)))

    def test_reopened_requires_prior_at_handoff(self):
        current = self.prior()
        current.reopened_from_hash = "0"*64
        self.assertIn("prior_required_for_reopened_investigation", _verify_reopen_lineage(current, None))

if __name__ == "__main__":
    unittest.main()
