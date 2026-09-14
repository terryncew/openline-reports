"""EARNED-MEMORY-001 integration and fail-closed regression tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from openline_reports.swarm.inheritance import (
    generation_context,
    guarded_strategy_evaluation,
    project_memory,
)


class EarnedMemoryProjectionUnitTests(unittest.TestCase):
    def test_candidate_requires_executed_receiver_state(self):
        candidate_hash = "b" * 64
        decision = {"decision": "PROMOTE", "receipt_hash": "d" * 64}
        state = {
            "generation": 0,
            "state_hash": "s" * 64,
            "current": {"version_hash": "a" * 64},
        }
        memory = project_memory(
            candidate_hash=candidate_hash,
            decision=decision,
            receiver_state=state,
            standing="ACTIVE",
        )
        self.assertEqual(memory["status"], "candidate")
        self.assertEqual(memory["survived"], 0)

    def test_reopened_memory_is_warning_not_inherited_context(self):
        candidate_hash = "b" * 64
        decision = {"decision": "PROMOTE", "receipt_hash": "d" * 64}
        state = {
            "generation": 1,
            "state_hash": "s" * 64,
            "current": {"version_hash": candidate_hash},
        }
        memory = project_memory(
            candidate_hash=candidate_hash,
            decision=decision,
            receiver_state=state,
            standing="REOPEN",
            claim_report_id="report:1",
        )
        context = generation_context([memory])
        self.assertEqual(memory["status"], "questioned")
        self.assertEqual(memory["survived"], 1)
        self.assertEqual(context["inherited"], [])
        self.assertEqual(len(context["warnings"]), 1)

    def test_constitutional_schema_guard_precedes_evaluator(self):
        calls = 0

        def validator(candidate):
            if set(candidate) != {"schema", "source_limit"}:
                raise ValueError("strategy_shape")

        def evaluator(_candidate):
            nonlocal calls
            calls += 1

        result = guarded_strategy_evaluation(
            {"schema": "research.swarm.strategy.v1", "source_limit": 8, "evaluator": "worker"},
            evaluator,
            validator=validator,
        )
        self.assertEqual(result["decision"], "DENY")
        self.assertFalse(result["evaluator_called"])
        self.assertEqual(calls, 0)


AVAILABLE = all(
    importlib.util.find_spec(name)
    for name in (
        "openline_lite",
        "olp_swarm_gate",
        "openline_proof_adapter",
        "openline_claim_graph",
    )
)


@unittest.skipUnless(AVAILABLE, "install requirements-swarm.txt for earned-memory integration")
class EarnedMemoryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from openline_reports.swarm.inheritance import (
            run_earned_memory_proof,
            verify_earned_memory_proof,
        )

        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "earned-memory-001"
        cls.summary = run_earned_memory_proof(cls.root)
        cls.verification = verify_earned_memory_proof(
            cls.root,
            expected_evaluator_public_key=cls.summary["evaluator_public_key"],
            expected_proof_adapter_public_key=cls.summary["proof_adapter_public_key"],
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_interruption_restart_invalidation_and_no_auto_rollback(self):
        self.assertEqual(
            self.summary["verdict"],
            "EARNED_MEMORY_DEFEASIBLE_INHERITANCE_ENFORCED",
        )
        self.assertEqual(
            self.summary["phase_statuses"],
            ["candidate", "inherited", "questioned"],
        )
        self.assertEqual(self.summary["receiver_generation"], 1)
        self.assertTrue(self.summary["installed_version_unchanged_after_reopen"])
        self.assertEqual(self.summary["standing_decision"], "REOPEN")
        self.assertEqual(self.summary["rollback_recommendation"], "ROLLBACK_ELIGIBLE")
        self.assertEqual(self.summary["rollback_execution_authority"], "NONE")
        self.assertFalse(self.summary["rollback_auto_execute"])
        self.assertEqual(self.summary["generation_2_inherited_count"], 0)
        self.assertEqual(self.summary["generation_2_warning_count"], 1)
        self.assertEqual(self.summary["constitutional_attack"], "DENY")
        self.assertEqual(self.summary["constitutional_attack_evaluator_calls"], 0)
        self.assertTrue(self.verification["verified"])
        self.assertTrue(self.verification["evaluation_recomputed"])
        self.assertTrue(self.verification["claim_graph_recomputed"])

    def test_persistence_requires_exact_stored_receipt(self):
        from openline_reports.swarm.inheritance import require_persisted_promotion
        decision = json.loads((self.root / "decision.json").read_text())
        self.assertNotIn("receipt_persisted", decision)
        require_persisted_promotion(decision, self.root / "promotion.jsonl")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipts.jsonl"
            with self.assertRaises(RuntimeError):
                require_persisted_promotion({**decision, "receipt_persisted": True}, path)
            path.write_text("")
            with self.assertRaises(RuntimeError):
                require_persisted_promotion(decision, path)
            shutil.copyfile(self.root / "promotion.jsonl", path)
            with self.assertRaises(RuntimeError):
                require_persisted_promotion({**decision, "proposal_id": "other"}, path)
            path.write_text(path.read_text() + "not-json\n")
            with self.assertRaises(RuntimeError):
                require_persisted_promotion(decision, path)

    def test_old_verified_memory_shape_is_preserved_but_derived(self):
        rows = [
            json.loads(line)
            for line in (self.root / "verified-memory.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
        self.assertEqual([row["status"] for row in rows], ["candidate", "inherited", "questioned"])
        for row in rows:
            self.assertTrue({"rid", "title", "text", "status", "survived", "witness", "reuse", "tags"} <= set(row))
            self.assertEqual(row["schema"], "openline.verified-memory.evidence-projection.v1")
            self.assertIn("evidence", row)

    def test_closed_proof_rejects_tamper(self):
        from openline_reports.swarm.inheritance import verify_earned_memory_proof

        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "copy"
            shutil.copytree(self.root, copy)
            target = copy / "memory-phase-2-inherited.json"
            data = json.loads(target.read_text(encoding="utf-8"))
            data["status"] = "candidate"
            target.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_earned_memory_proof(
                    copy,
                    expected_evaluator_public_key=self.summary["evaluator_public_key"],
                    expected_proof_adapter_public_key=self.summary["proof_adapter_public_key"],
                )


if __name__ == "__main__":
    unittest.main()
