"""Integration tests; optional swarm dependencies are installed by the swarm CI."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

AVAILABLE = all(importlib.util.find_spec(name) for name in ("openline_lite", "olp_swarm_gate"))
if AVAILABLE:
    from openline_reports.swarm.runtime import run, verify, fixture_agent, command_agent, BASELINE, CANDIDATE, dumps, strategy_check
    from openline_reports.swarm.experiment import demo, verify_demo, cases, loads
    from olp_swarm_gate import ReceiverStateStore, ReceiverPromotionExecutor, ReceiverStateError


@unittest.skipUnless(AVAILABLE, "install requirements-swarm.txt for swarm integration tests")
class ResearchSwarmTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, pack=None, agent=fixture_agent, strategy=CANDIDATE):
        return run(pack or cases()[0][0], strategy, self.root / "run", agent)

    def test_three_roles_checked_handoffs_and_research_contract(self):
        result = self.execute()
        self.assertEqual((result["status"], result["calls"]), ("supported", 3))
        self.assertEqual(result["runtime_permission"], "NONE")
        root = self.root / "run"
        m = loads((root / "manifest.json").read_bytes())
        self.assertTrue(verify(root, m["body"]["public_key"])["verified"])
        inv = loads((root / "investigation.json").read_bytes())
        self.assertEqual(inv["disposition"], "candidate")
        self.assertEqual(len(loads((root / "handoffs.json").read_bytes())), 3)

    def test_conflict_cannot_be_outvoted(self):
        result = self.execute(pack=cases()[1][0])
        self.assertEqual(result["status"], "unresolved")
        self.assertIn("active sources disagree", result["reasons"])

    def test_missing_source_is_not_agreement(self):
        result = self.execute(strategy=BASELINE)
        self.assertEqual(result["status"], "unresolved")

    def test_withdrawn_source_does_not_earn_support(self):
        self.assertEqual(self.execute(pack=cases()[2][0])["status"], "unresolved")

    def test_forged_fact_rejected_by_lite(self):
        def liar(req):
            out = fixture_agent(req)
            if req["role"] == "proposer":
                out["findings"][0]["value"] = 9000
            return out
        self.assertEqual(self.execute(agent=liar)["status"], "quarantine")

    def test_synthesizer_cannot_erase_uncertainty(self):
        def liar(req):
            return {"status": "supported", "answer": 12} if req["role"] == "synthesizer" else fixture_agent(req)
        self.assertEqual(self.execute(pack=cases()[1][0], agent=liar)["status"], "quarantine")

    def test_critic_objection_survives(self):
        def critic(req):
            return {"objections": ["Locator needs independent review"]} if req["role"] == "critic" else fixture_agent(req)
        result = self.execute(agent=critic)
        self.assertEqual(result["status"], "unresolved")
        self.assertIn("Locator needs independent review", result["reasons"])

    def test_worker_cannot_introduce_unregistered_source(self):
        def liar(req):
            return {"findings": [{"source_id": "invented", "value": 12}]} if req["role"] == "proposer" else fixture_agent(req)
        self.assertEqual(self.execute(agent=liar)["status"], "quarantine")

    def test_signed_evidence_tamper_fails(self):
        self.execute()
        root = self.root / "run"
        m = loads((root / "manifest.json").read_bytes())
        (root / "sources.json").write_text('{}')
        with self.assertRaises(ValueError):
            verify(root, m["body"]["public_key"])

    def test_wrong_trust_anchor_fails(self):
        self.execute()
        with self.assertRaises(ValueError):
            verify(self.root / "run", "00" * 32)

    def test_unexpected_file_fails_closed(self):
        self.execute()
        root = self.root / "run"
        m = loads((root / "manifest.json").read_bytes())
        (root / "extra.json").write_text('{}')
        with self.assertRaises(ValueError):
            verify(root, m["body"]["public_key"])

    def test_strategy_cannot_edit_rules_or_exceed_budget(self):
        for strategy in ({**CANDIDATE, "max_calls": 999}, {**CANDIDATE, "source_limit": 9},
                         {**CANDIDATE, "source_limit": True}):
            with self.assertRaises(ValueError):
                strategy_check(strategy)

    def test_promotion_runs_new_strategy_and_verifies(self):
        root = self.root / "demo"
        summary = demo(root)
        self.assertEqual(summary["decision"], "PROMOTE")
        self.assertEqual(summary["generation"], 1)
        self.assertEqual(summary["next_job_status"], "supported")
        self.assertTrue(verify_demo(root, summary["evaluator_public_key"])["evaluation_recomputed"])

    def test_tie_keeps_incumbent(self):
        root = self.root / "demo"
        summary = demo(root, BASELINE)
        self.assertEqual(summary["decision"], "QUARANTINE")
        self.assertEqual(summary["generation"], 0)
        self.assertEqual(summary["next_job_status"], "unresolved")
        verify_demo(root, summary["evaluator_public_key"])

    def test_partial_improvement_is_rejected(self):
        root = self.root / "demo"
        summary = demo(root, {**CANDIDATE, "source_limit": 2})
        self.assertEqual(summary["decision"], "REJECT")
        self.assertEqual(summary["generation"], 0)
        verify_demo(root, summary["evaluator_public_key"])

    def test_boolean_cannot_impersonate_integer(self):
        pack = copy.deepcopy(cases()[0][0])
        for source in pack["sources"]:
            source["data"]["limit"] = 1
        def liar(req):
            out = fixture_agent(req)
            if req["role"] == "proposer":
                out["findings"][0]["value"] = True
            return out
        self.assertEqual(self.execute(pack=pack, agent=liar)["status"], "quarantine")

    def test_promotion_cannot_be_replayed(self):
        root = self.root / "demo"
        demo(root)
        store = ReceiverStateStore(str(root / "receiver.json"), str(root / "artifacts"))
        executor = ReceiverPromotionExecutor(decision_receipt_path=str(root / "promotion.jsonl"), state_store=store)
        with self.assertRaises(ReceiverStateError):
            executor.execute(promotion_receipt=loads((root / "decision.json").read_bytes()),
                             candidate_artifact_path=root / "candidate.json", now=9999999999)
        self.assertEqual(store.read()["generation"], 1)

    def test_evaluation_tamper_fails(self):
        root = self.root / "demo"
        summary = demo(root)
        (root / "evaluation.json").write_text('{}')
        with self.assertRaises(ValueError):
            verify_demo(root, summary["evaluator_public_key"])

    def test_external_command_bridge(self):
        bridge = self.root / "bridge.py"
        bridge.write_text('import json,sys\nfrom openline_reports.swarm.runtime import fixture_agent\nprint(json.dumps(fixture_agent(json.load(sys.stdin))))\n')
        result = self.execute(agent=command_agent([sys.executable, str(bridge)]))
        self.assertEqual(result["agent_mode"], "external-adapter")
        self.assertEqual(result["status"], "supported")

    def test_adapter_timeout_preserves_quarantine(self):
        adapter = command_agent([sys.executable, "-c", "import time; time.sleep(5)"], timeout=.05)
        result = self.execute(agent=adapter)
        self.assertEqual(result["status"], "quarantine")
        self.assertEqual(result["calls"], 1)

    def test_adapter_output_limit(self):
        adapter = command_agent([sys.executable, "-c", "print('x'*300000)"])
        self.assertEqual(self.execute(agent=adapter)["status"], "quarantine")

    def test_duplicate_sources_rejected(self):
        pack = copy.deepcopy(cases()[0][0])
        pack["sources"][1]["id"] = pack["sources"][0]["id"]
        with self.assertRaises(ValueError):
            self.execute(pack=pack)

    def test_strategy_proposer_has_no_approval_power(self):
        def bad(req):
            return {**CANDIDATE, "approved": True}
        with self.assertRaises(ValueError):
            demo(self.root / "demo", strategy_agent=bad)
        self.assertFalse((self.root / "demo" / "receiver.json").exists())
