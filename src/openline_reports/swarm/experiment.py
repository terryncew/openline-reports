"""RESEARCH-SWARM-001: fixed synthetic evaluation and exact strategy replacement.

Known-answer cases are public controls, not a secret held-out scientific test.
Only a source-selection strategy can change; rules, roles, and checker cannot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def loads(raw):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise ValueError("duplicate_key")
            d[k] = v
        return d
    def bad(value):
        raise ValueError("nonfinite")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
from olp_swarm_gate import (
    EvalAirlockAppraisal, ReceiverPromotionExecutor, ReceiverStateStore,
    SuccessorProposal, SuccessorPromotionGate, SuccessorPromotionPolicy,
    evaluator_key_fingerprint, materialize_appraisal_receipt, public_key_hex,
    verify_receiver_state_file,
)
from .runtime import BASELINE, CANDIDATE, RULES, digest, run, strategy_check, verify, command_agent, fixture_agent


def dumps(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def object_hash(value):
    return digest(dumps(value))


def write(path, value):
    path.write_bytes(dumps(value))


def cases():
    def pack(name, values, standings=None):
        return {"id": name, "question": "Do the active records agree on the reported limit?",
                "pointer": "/limit", "sources": [
                    {"id": f"source-{i}", "locator": f"fixture://{name}/{i}",
                     "standing": (standings or ["active"] * len(values))[i], "data": {"limit": v}}
                    for i, v in enumerate(values)]}
    return [
        (pack("agreement", [12, 12]), {"status": "supported", "answer": 12}),
        (pack("conflict", [12, 15]), {"status": "unresolved", "answer": None}),
        (pack("withdrawn", [12], ["withdrawn"]), {"status": "unresolved", "answer": None}),
        (pack("three-sources", [7, 7, 7]), {"status": "supported", "answer": 7}),
    ]


def evaluate(strategy: dict, root: Path) -> dict:
    strategy_check(strategy)
    root.mkdir(parents=True, exist_ok=False)
    rows = []
    for pack, expected in cases():
        target = root / pack["id"]
        result = run(pack, strategy, target)
        manifest = loads((target / "manifest.json").read_bytes())
        verify(target, manifest["body"]["public_key"])
        actual = {k: result[k] for k in ("status", "answer")}
        correct = actual == expected
        critical = actual["status"] == "supported" and not correct
        rows.append({"case": pack["id"], "actual": actual, "expected": expected,
                     "correct": correct, "critical": critical, "calls": result["calls"],
                     "run_manifest_sha256": digest((target / "manifest.json").read_bytes())})
    return {"rows": rows, "score": sum(x["correct"] for x in rows) / len(rows),
            "critical_failures": sum(x["critical"] for x in rows),
            "cases_sha256": object_hash(cases()), "rules_sha256": object_hash(RULES),
            "strategy_sha256": digest(dumps(strategy)), "mode": "synthetic-fixture"}


def demo(root: Path, candidate: dict | None = None, strategy_agent=fixture_agent) -> dict:
    request = {"role": "strategy-proposer", "baseline": BASELINE, "receiver_rules": RULES,
               "task": "Propose source_limit only to improve complete source coverage within the fixed budget."}
    candidate = strategy_agent(request) if candidate is None else candidate
    strategy_check(candidate)
    root.mkdir(parents=True, exist_ok=False)
    write(root / "strategy-proposal-request.json", request)
    write(root / "incumbent.json", BASELINE)
    write(root / "candidate.json", candidate)
    # Freeze inputs before either lane executes. Worker code receives no checker key.
    write(root / "registration.json", {"rules": RULES, "cases": cases(),
          "baseline_hash": digest(dumps(BASELINE)), "candidate_hash": digest(dumps(candidate)),
          "minimum_gain": 0.25, "max_critical_failures": 0, "max_calls_per_case": 3})
    baseline = evaluate(BASELINE, root / "baseline")
    successor = evaluate(candidate, root / "candidate")
    evaluation = {"baseline": baseline, "candidate": successor,
                  "registration_sha256": digest((root / "registration.json").read_bytes())}
    write(root / "evaluation.json", evaluation)
    key = Ed25519PrivateKey.generate()
    pub = public_key_hex(key)
    now = time.time()
    policy = SuccessorPromotionPolicy(
        receipt_path=str(root / "promotion.jsonl"), appraisal_receipt_dir=str(root / "appraisals"),
        expected_evaluator_id="research-swarm-checker", expected_evaluator_hash=evaluator_key_fingerprint(pub),
        expected_evaluator_public_key=pub, expected_benchmark_id="RESEARCH-SWARM-001",
        expected_benchmark_version="1", expected_benchmark_owner="receiver",
        expected_heldout_set_hash=object_hash(cases()), expected_policy_hash=object_hash(RULES),
        min_heldout_delta=0.25, min_candidate_score=1.0, max_critical_failures=0,
        require_evaluation_artifact_hash=True,
        receiver_state_path=str(root / "receiver.json"), receiver_artifact_dir=str(root / "artifacts"))
    write(root / "evaluator-public-key.json", {"public_key": pub})
    write(root / "promotion-policy.json", policy.frozen_public_dict())
    store = ReceiverStateStore(policy.receiver_state_path, policy.receiver_artifact_dir)
    store.initialize(version_id="source-limit-1", version_hash=digest(dumps(BASELINE)), now=now,
                     artifact_path=root / "incumbent.json")
    proposal = SuccessorProposal("research-strategy-1", "strategy-proposer", "source-limit-1",
        digest(dumps(BASELINE)), "candidate-strategy", digest(dumps(candidate)),
        "Propose wider source coverage under unchanged receiver rules and call budget.", now)
    appraisal = EvalAirlockAppraisal("", policy.expected_evaluator_id, policy.expected_evaluator_hash,
        policy.expected_benchmark_id, policy.expected_benchmark_version, policy.expected_benchmark_owner,
        policy.expected_heldout_set_hash, policy.expected_policy_hash, object_hash(evaluation),
        proposal.source_version_hash, proposal.successor_version_hash, baseline["score"], successor["score"],
        successor["critical_failures"], True, "SUPPORTED", now,
        evaluation_artifact_hash=digest((root / "evaluation.json").read_bytes()))
    appraisal = materialize_appraisal_receipt(appraisal, policy.appraisal_receipt_dir, signing_key=key)
    decision = SuccessorPromotionGate(policy).evaluate(proposal=proposal, appraisal=appraisal, now=now)
    write(root / "decision.json", decision)
    if decision["decision"] == "PROMOTE":
        ReceiverPromotionExecutor(decision_receipt_path=policy.receipt_path, state_store=store).execute(
            promotion_receipt=decision, candidate_artifact_path=root / "candidate.json", now=now)
    # Actually use the receiver's current archived strategy for the next run.
    state = store.read()
    current_hash = state["current"]["version_hash"]
    artifact = next(p for p in (root / "artifacts").rglob("*") if p.is_file() and digest(p.read_bytes()) == current_hash)
    next_result = run(cases()[0][0], loads(artifact.read_bytes()), root / "next-job")
    summary = {"experiment": "RESEARCH-SWARM-001", "mode": "synthetic-fixture",
               "baseline_score": baseline["score"], "candidate_score": successor["score"],
               "decision": decision["decision"], "generation": state["generation"],
               "next_job_status": next_result["status"], "runtime_permission": "NONE"}
    summary["evaluator_public_key"] = pub
    write(root / "summary.json", summary)
    files = {p.relative_to(root).as_posix(): digest(p.read_bytes())
             for p in sorted(root.rglob("*")) if p.is_file()}
    seal = {"files": files, "public_key": pub, "schema": "research.swarm.experiment.v1"}
    write(root / "experiment-seal.json", {"body": seal, "signature": key.sign(dumps(seal)).hex()})
    return summary


def verify_demo(root: Path, expected_public_key: str) -> dict:
    """Recompute fixture metrics and verify each run plus signed gate appraisal."""
    from olp_swarm_gate import EvalAirlockAppraisal, verify_materialized_appraisal_receipt, verify_chain
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    sealed = loads((root / "experiment-seal.json").read_bytes())
    body = sealed["body"]
    if body["public_key"] != expected_public_key:
        raise ValueError("evaluator_key_mismatch")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(expected_public_key)).verify(
        bytes.fromhex(sealed["signature"]), dumps(body))
    files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != root / "experiment-seal.json"}
    if files != set(body["files"]):
        raise ValueError("experiment_closure")
    for name, expected in body["files"].items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or digest(path.read_bytes()) != expected:
            raise ValueError("experiment_artifact_changed")
    evaluation = loads((root / "evaluation.json").read_bytes())
    registration = loads((root / "registration.json").read_bytes())
    if registration["rules"] != RULES or registration["cases"] != loads(dumps(cases())):
        raise ValueError("frozen_evaluator_mismatch")
    if evaluation["registration_sha256"] != digest((root / "registration.json").read_bytes()):
        raise ValueError("registration_binding")
    for lane, strategy_file in (("baseline", "incumbent.json"), ("candidate", "candidate.json")):
        strategy = loads((root / strategy_file).read_bytes())
        with tempfile.TemporaryDirectory() as td:
            replay = evaluate(strategy, Path(td) / "replay")
        saved = evaluation[lane]
        for key in ("score", "critical_failures", "cases_sha256", "rules_sha256", "strategy_sha256"):
            if saved[key] != replay[key]:
                raise ValueError("evaluation_mismatch")
        for original, recomputed in zip(saved["rows"], replay["rows"], strict=True):
            for key in ("case", "actual", "expected", "correct", "critical", "calls"):
                if original[key] != recomputed[key]:
                    raise ValueError("case_result_mismatch")
            run_root = root / lane / original["case"]
            if digest((run_root / "manifest.json").read_bytes()) != original["run_manifest_sha256"]:
                raise ValueError("run_binding")
            manifest = loads((run_root / "manifest.json").read_bytes())
            verify(run_root, manifest["body"]["public_key"])
    decision = loads((root / "decision.json").read_bytes())
    if not verify_chain(str(root / "promotion.jsonl"))["valid"]:
        raise ValueError("promotion_chain")
    persisted = [loads(line) for line in (root / "promotion.jsonl").read_bytes().splitlines()]
    if decision not in persisted:
        raise ValueError("decision_not_persisted")
    if not verify_receiver_state_file(root / "receiver.json")["valid"]:
        raise ValueError("receiver_history")
    # Appraisal signature and evaluation binding are checked explicitly below.
    public = loads((root / "evaluator-public-key.json").read_bytes())["public_key"]
    appraisal_files = list((root / "appraisals").glob("*.json"))
    if len(appraisal_files) != 1:
        raise ValueError("appraisal_count")
    doc = loads(appraisal_files[0].read_bytes())
    app = EvalAirlockAppraisal(appraisal_receipt_hash=appraisal_files[0].stem, **doc["appraisal"])
    errors = verify_materialized_appraisal_receipt(app, root / "appraisals", expected_public_key=expected_public_key)
    if errors:
        raise ValueError("appraisal_signature:" + ",".join(errors))
    if app.evaluation_artifact_hash != digest((root / "evaluation.json").read_bytes()):
        raise ValueError("appraisal_evaluation_binding")
    if app.baseline_score != evaluation["baseline"]["score"] or app.candidate_score != evaluation["candidate"]["score"]:
        raise ValueError("appraisal_metrics")
    if app.source_version_hash != digest((root / "incumbent.json").read_bytes()) or app.successor_version_hash != digest((root / "candidate.json").read_bytes()):
        raise ValueError("appraisal_candidate_binding")
    if decision["appraisal_receipt_hash"] != app.appraisal_receipt_hash:
        raise ValueError("decision_appraisal_binding")
    wanted = "PROMOTE" if app.candidate_score == 1.0 and app.candidate_score - app.baseline_score >= 0.25 and app.critical_failures == 0 else "REJECT"
    if app.source_version_hash == app.successor_version_hash:
        wanted = "QUARANTINE"
    if decision["decision"] != wanted:
        raise ValueError("decision_evaluation_mismatch")
    state = loads((root / "receiver.json").read_bytes())
    expected_hash = app.successor_version_hash if wanted == "PROMOTE" else app.source_version_hash
    if state["current"]["version_hash"] != expected_hash or state["generation"] != int(wanted == "PROMOTE"):
        raise ValueError("executed_state_mismatch")
    next_manifest = loads((root / "next-job" / "manifest.json").read_bytes())
    verify(root / "next-job", next_manifest["body"]["public_key"])
    if digest((root / "next-job" / "strategy.json").read_bytes()) != expected_hash:
        raise ValueError("next_job_strategy_mismatch")
    return {"verified_runs": len(cases()) * 2, "evaluation_recomputed": True,
            "decision": decision["decision"], "appraisal_file": appraisal_files[0].name,
            "public_key": public}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("demo", "verify-demo"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path, required=True)
        if name == "verify-demo":
            p.add_argument("--public-key", required=True)
        else:
            p.add_argument("--strategy-command", help="JSON argv for a trusted strategy-proposer bridge")
            p.add_argument("--candidate", type=Path, help="Exact proposed strategy JSON; omitted uses fixture proposal")
    p = sub.add_parser("run")
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--strategy", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--agent-command", help="JSON argv array for a trusted stdin/stdout bridge")
    p = sub.add_parser("verify")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--public-key", required=True)
    args = parser.parse_args()
    if args.command == "demo":
        if args.candidate and args.strategy_command:
            parser.error("use either --candidate or --strategy-command")
        kwargs = {"strategy_agent": command_agent(json.loads(args.strategy_command))} if args.strategy_command else {}
        result = demo(args.out, loads(args.candidate.read_bytes()) if args.candidate else None, **kwargs)
    elif args.command == "verify-demo":
        result = verify_demo(args.out, args.public_key)
    elif args.command == "verify":
        result = verify(args.out, args.public_key)
    else:
        kw = {"agent": command_agent(json.loads(args.agent_command))} if args.agent_command else {}
        result = run(loads(args.pack.read_bytes()), loads(args.strategy.read_bytes()), args.out, **kw)
    print(json.dumps(result, indent=2))
    return 1 if result.get("status") == "quarantine" else 0


if __name__ == "__main__":
    raise SystemExit(main())
