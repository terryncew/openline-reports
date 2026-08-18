import unittest
from openline_reports.model import Investigation, Claim, SourceRef, Objection
from openline_reports.gate import validate_investigation

class GateTests(unittest.TestCase):
    def valid_candidate(self):
        return Investigation(
            "x", "t", "q", "h",
            sources=[SourceRef("s1", "src", "loc", standing="active")],
            claims=[Claim("c1", "claim", "supported", ["s1"])],
            objections=[Objection("o1", "c1", "challenge", "basis", True, "resolved by source")],
            discovery_delta="we learned something",
            result_summary="bounded result",
            disposition="candidate",
        )

    def test_candidate_requires_delta_and_summary(self):
        inv = Investigation("x", "t", "q", "h", disposition="candidate")
        errs = validate_investigation(inv)
        self.assertIn("discovery_delta_required", errs)
        self.assertIn("result_summary_required", errs)

    def test_empty_candidate_fails_closed(self):
        inv = Investigation(
            "x","t","q","h",
            discovery_delta="d", result_summary="r", disposition="candidate"
        )
        errs = validate_investigation(inv)
        self.assertIn("candidate_requires_sources", errs)
        self.assertIn("candidate_requires_claims", errs)
        self.assertIn("candidate_requires_supported_claim", errs)

    def test_supported_claim_requires_basis(self):
        inv = Investigation(
            "x", "t", "q", "h",
            claims=[Claim("c1", "claim", "supported")],
            discovery_delta="changed", result_summary="result", disposition="pivot"
        )
        errs = validate_investigation(inv)
        self.assertIn("supported_claim_without_basis:c1", errs)
        self.assertIn("supported_claim_without_active_basis:c1", errs)

    def test_withdrawn_source_cannot_support_claim(self):
        inv = Investigation(
            "x","t","q","h",
            sources=[SourceRef("s1","withdrawn","loc",standing="withdrawn")],
            claims=[Claim("c1","claim","supported",["s1"])],
            discovery_delta="d", result_summary="r", disposition="candidate"
        )
        self.assertIn("supported_claim_without_active_basis:c1", validate_investigation(inv))

    def test_questioned_source_cannot_be_sole_support(self):
        inv = Investigation(
            "x","t","q","h",
            sources=[SourceRef("s1","questioned","loc",standing="questioned")],
            claims=[Claim("c1","claim","supported",["s1"])],
            discovery_delta="d", result_summary="r", disposition="candidate"
        )
        self.assertIn("supported_claim_without_active_basis:c1", validate_investigation(inv))

    def test_supported_claim_cannot_depend_on_withdrawn_claim(self):
        inv = Investigation(
            "x","t","q","h",
            sources=[SourceRef("s1","src","loc")],
            claims=[
                Claim("c1","prior","withdrawn",["s1"]),
                Claim("c2","downstream","supported",depends_on=["c1"]),
            ],
            discovery_delta="d", result_summary="r", disposition="pivot"
        )
        errs = validate_investigation(inv)
        self.assertTrue(any(e.startswith("supported_claim_depends_on_non_supported:c2:c1") for e in errs))
        self.assertIn("supported_claim_invalid_dependency_basis:c2", errs)

    def test_missing_alternative_fails(self):
        inv = self.valid_candidate()
        inv.claims[0].alternatives = ["does-not-exist"]
        self.assertIn(
            "missing_claim_alternatives:c1:does-not-exist",
            validate_investigation(inv)
        )

    def test_dependency_cycle_fails(self):
        inv = Investigation(
            "x","t","q","h",
            sources=[SourceRef("s1","src","loc")],
            claims=[
                Claim("c1","one","supported",["s1"],depends_on=["c2"]),
                Claim("c2","two","supported",["s1"],depends_on=["c1"]),
            ],
            discovery_delta="d", result_summary="r", disposition="candidate"
        )
        self.assertTrue(any(e.startswith("dependency_cycle:") for e in validate_investigation(inv)))

    def test_invalid_objection_target_fails(self):
        inv = self.valid_candidate()
        inv.objections = [Objection("o1","missing","challenge","basis",True,"resolved")]
        self.assertIn("invalid_objection_target:o1:missing", validate_investigation(inv))

    def test_runtime_source_standing_fails(self):
        inv = self.valid_candidate()
        inv.sources[0].standing = "banana"
        self.assertIn("invalid_source_standing:s1:banana", validate_investigation(inv))

    def test_runtime_claim_status_fails(self):
        inv = self.valid_candidate()
        inv.claims[0].status = "definitely"
        self.assertIn("invalid_claim_status:c1:definitely", validate_investigation(inv))

    def test_runtime_disposition_fails(self):
        inv = self.valid_candidate()
        inv.disposition = "publish"
        self.assertIn("invalid_disposition:publish", validate_investigation(inv))

    def test_unresolved_claim_requires_uncertainty(self):
        inv = Investigation(
            "x", "t", "q", "h",
            sources=[SourceRef("s1", "src", "loc")],
            claims=[Claim("c1", "claim", "unresolved", ["s1"])],
            discovery_delta="changed", result_summary="result", disposition="pivot"
        )
        self.assertIn("unresolved_claim_missing_uncertainty:c1", validate_investigation(inv))

    def test_unresolved_objection_blocks_candidate(self):
        inv = self.valid_candidate()
        inv.objections = [Objection("o1", "c1", "challenge", "basis")]
        self.assertIn("unresolved_objections_present:o1", validate_investigation(inv))

    def test_clean_candidate_passes(self):
        self.assertEqual(validate_investigation(self.valid_candidate()), [])

    def test_kill_requires_reason(self):
        inv = Investigation("x", "t", "q", "h", disposition="kill")
        self.assertIn("kill_reason_required", validate_investigation(inv))

    def test_handoff_validation_requires_disposition(self):
        inv = Investigation("x","t","q","h")
        self.assertIn(
            "disposition_required_for_handoff",
            validate_investigation(inv, require_disposition=True)
        )

    def test_reopen_hash_shape_is_enforced(self):
        inv = self.valid_candidate()
        inv.reopened_from_hash = "not-a-hash"
        self.assertIn("invalid_reopened_from_hash", validate_investigation(inv))

if __name__ == "__main__":
    unittest.main()
