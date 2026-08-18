from __future__ import annotations
import copy
from openline_reports.model import Investigation, SourceRef, Claim, Objection
from openline_reports.gate import validate_investigation

def base_candidate():
    return Investigation(
        "probe","Probe","What survives?","Initial hypothesis",
        sources=[SourceRef("s1","active source","fixture://s1",standing="active")],
        claims=[Claim("c1","supported claim","supported",["s1"])],
        discovery_delta="changed",
        result_summary="bounded result",
        disposition="candidate",
    )

def must_fail(name, inv, needle):
    errors = validate_investigation(inv)
    if not any(needle in e for e in errors):
        raise AssertionError(f"{name}: expected {needle!r}, got {errors}")
    print(f"PASS reject {name}: {errors}")

def main():
    inv = Investigation("x","t","q","h",discovery_delta="d",result_summary="r",disposition="candidate")
    must_fail("empty_candidate", inv, "candidate_requires_claims")

    inv = base_candidate()
    inv.sources[0].standing = "withdrawn"
    must_fail("withdrawn_only_basis", inv, "supported_claim_without_active_basis")

    inv = base_candidate()
    inv.claims.insert(0, Claim("c0","withdrawn upstream","withdrawn",["s1"]))
    inv.claims[1].source_ids = []
    inv.claims[1].depends_on = ["c0"]
    inv.disposition = "pivot"
    must_fail("withdrawn_dependency", inv, "supported_claim_depends_on_non_supported")

    inv = base_candidate()
    inv.claims[0].alternatives = ["missing"]
    must_fail("missing_alternative", inv, "missing_claim_alternatives")

    inv = base_candidate()
    inv.claims.append(Claim("c2","second","supported",["s1"],depends_on=["c1"]))
    inv.claims[0].depends_on = ["c2"]
    must_fail("dependency_cycle", inv, "dependency_cycle")

    inv = base_candidate()
    inv.objections = [Objection("o1","missing","challenge","basis",True,"resolved")]
    must_fail("missing_objection_target", inv, "invalid_objection_target")

    inv = base_candidate()
    inv.sources[0].standing = "banana"
    must_fail("invalid_source_standing", inv, "invalid_source_standing")

    inv = base_candidate()
    inv.claims[0].status = "definitely"
    must_fail("invalid_claim_status", inv, "invalid_claim_status")

    inv = base_candidate()
    inv.disposition = "publish"
    must_fail("invalid_disposition", inv, "invalid_disposition")

    inv = Investigation("x","t","q","h")
    must_fail("missing_handoff_disposition", inv, "disposition_required_for_handoff") if False else None
    errors = validate_investigation(inv, require_disposition=True)
    if "disposition_required_for_handoff" not in errors:
        raise AssertionError(errors)
    print("PASS reject missing_handoff_disposition:", errors)

    print("hostile_contract_probe: PASS")

if __name__ == "__main__":
    main()
