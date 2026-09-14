"""EARNED-MEMORY-001: defeasible inheritance across interrupted promotion.

This module composes the existing research-swarm evaluator, receiver-owned
successor promotion, Proof Adapter boundary receipts, Claim Graph standing, and
Verified Memory's public JSONL shape. It does not create a second evaluator or
promotion engine.

The proof is deliberately narrow:

* a PROMOTE decision is not inherited before receiver execution;
* restart plus the exact persisted promotion can earn inherited status;
* later admitted evidence loss removes inherited standing without silently
  rolling back the installed receiver version; and
* a worker proposal that tries to alter evaluator/policy fields is rejected by
  the frozen data-only strategy schema before evaluation is invoked.

Proof Adapter receipts remain self/provisional observations. Inheritance is
reconstructed from the underlying receiver/evaluation/standing evidence.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterable

EXPERIMENT_ID = "EARNED-MEMORY-001"
VERDICT = "EARNED_MEMORY_DEFEASIBLE_INHERITANCE_ENFORCED"
ADAPTER_KEY_ID = "earned-memory-receiver-001"
MEMORY_SCHEMA = "openline.verified-memory.evidence-projection.v1"


def dumps(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps(value))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(dumps(value) + b"\n")


def _current_hash(receiver_state: dict[str, Any]) -> str | None:
    current = receiver_state.get("current")
    return str(current.get("version_hash")) if isinstance(current, dict) else None


def project_memory(
    *,
    candidate_hash: str,
    decision: dict[str, Any],
    receiver_state: dict[str, Any],
    standing: str,
    claim_report_id: str | None = None,
) -> dict[str, Any]:
    """Derive the old Verified Memory shape from independently checked state.

    Callers do not supply ``status``, ``survived`` or ``witness``. Those fields
    are projections of persisted promotion state plus current standing.
    """

    promoted = (
        decision.get("decision") == "PROMOTE"
        and isinstance(receiver_state.get("generation"), int)
        and not isinstance(receiver_state.get("generation"), bool)
        and int(receiver_state["generation"]) >= 1
        and _current_hash(receiver_state) == candidate_hash
    )

    if standing == "REOPEN" and promoted:
        status = "questioned"
    elif standing == "QUARANTINE":
        status = "quarantined"
    elif promoted:
        status = "inherited"
    else:
        status = "candidate"

    survived = 1 if promoted else 0
    witness = "checkpoint receipt" if promoted else "none"
    reuse = {
        "candidate": "Do not inherit before exact receiver promotion completes.",
        "inherited": "May be supplied as earned prior to the next generation while standing remains current.",
        "questioned": "Warning only; do not treat as established while supporting standing is reopened.",
        "quarantined": "Preserve as a failure warning; do not reuse as an established lesson.",
    }[status]

    return {
        "rid": f"earned-memory:{candidate_hash}",
        "title": "Wider source coverage under unchanged receiver rules",
        "text": "The promoted source-selection strategy checks the full admitted source set before synthesis.",
        "status": status,
        "survived": survived,
        "witness": witness,
        "reuse": reuse,
        "tags": ["research-swarm", "source-coverage", "earned-memory"],
        "schema": MEMORY_SCHEMA,
        "evidence": {
            "candidate_hash": candidate_hash,
            "promotion_decision": decision.get("decision"),
            "promotion_decision_receipt_hash": decision.get("receipt_hash"),
            "receiver_generation": receiver_state.get("generation"),
            "receiver_state_hash": receiver_state.get("state_hash"),
            "receiver_current_hash": _current_hash(receiver_state),
            "standing": standing,
            "claim_report_id": claim_report_id,
            "projection_rule": (
                "candidate until exact receiver promotion; inherited only while exact promoted state "
                "retains standing; questioned after standing reopens"
            ),
        },
    }


def generation_context(memories: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Only currently inherited lessons enter established next-generation context."""

    memories = list(memories)
    inherited = [item for item in memories if item.get("status") == "inherited"]
    warnings = [
        item
        for item in memories
        if item.get("status") in {"questioned", "quarantined"}
    ]
    return {
        "schema": "openline.research-swarm.generation-context.v1",
        "inherited": inherited,
        "warnings": warnings,
    }


def guarded_strategy_evaluation(
    candidate: dict[str, Any],
    evaluator: Callable[[dict[str, Any]], Any],
    *,
    validator: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Reject non-strategy/constitutional fields before evaluator invocation."""

    if validator is None:
        from .runtime import strategy_check

        validator = strategy_check
    try:
        validator(candidate)
    except (TypeError, ValueError) as exc:
        return {
            "decision": "DENY",
            "reason": "CONSTITUTIONAL_MUTATION_DENIED",
            "detail": str(exc),
            "evaluator_called": False,
        }
    evaluator(candidate)
    return {
        "decision": "ADMITTED_FOR_EVALUATION",
        "reason": "STRATEGY_SCHEMA_ADMITTED",
        "evaluator_called": True,
    }


def _emit_memory_boundary(adapter: Any, memory: dict[str, Any], event_id: str, note: str) -> dict[str, Any]:
    from openline_proof_adapter import BoundaryEvent

    decision, receipt = adapter.observe(
        BoundaryEvent(
            run_id=EXPERIMENT_ID.lower(),
            event_id=event_id,
            system="openline-verified-memory",
            event_type="workflow_state",
            action="project_memory_state",
            payload={
                "workflow_name": "earned-memory-projection",
                "workflow": memory,
                "active": True,
                "change_note": note,
            },
        )
    )
    if decision.disposition != "COMMIT":
        raise RuntimeError(f"proof_adapter_memory_projection_not_committed:{decision.disposition}")
    return receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt.__dict__)


def _claim_graph_reopen(root: Path, support_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from openline_claim_graph import (
        analyze_source_impact,
        build_source,
        create_claim,
        create_impact_policy,
        create_snapshot,
        create_source_status_event,
        provenance_anchor,
    )

    support_source = build_source(support_text, locator="receiver://earned-memory/support")
    notice_text = "Receiver withdrew the supporting evidence for the promoted research strategy."
    notice_source = build_source(notice_text, locator="receiver://earned-memory/withdrawal")
    support_anchor = provenance_anchor(
        support_source,
        support_text,
        mode="QUOTE",
        asserted_by="earned-memory-receiver",
    )
    claim = create_claim(
        kind="OUTCOME",
        text=support_text,
        asserted_by="earned-memory-receiver",
        provenance=[support_anchor],
    )
    snapshot = create_snapshot(claims=[claim], relations=[])
    policy = create_impact_policy(
        snapshot,
        hard_relation_ids=[],
        decision_claim_ids=[claim["claim_id"]],
    )
    notice_anchor = provenance_anchor(
        notice_source,
        notice_text,
        mode="QUOTE",
        asserted_by="earned-memory-receiver",
    )
    event = create_source_status_event(
        status="WITHDRAWN",
        affected=[{"source_id": support_source["source_id"]}],
        evidence=[notice_anchor],
        asserted_by="earned-memory-receiver",
        effective_at="2026-09-14T00:00:00Z",
        reason="Prerequisite proof deliberately reopens the supporting evidence after promotion.",
    )
    sources = {
        support_source["source_id"]: support_source,
        notice_source["source_id"]: notice_source,
    }
    report = analyze_source_impact(snapshot, sources, event, policy)

    bundle = {
        "support_source": support_source,
        "notice_source": notice_source,
        "sources": sources,
        "claim": claim,
        "snapshot": snapshot,
        "policy": policy,
        "event": event,
    }
    write(root / "claim-graph-inputs.json", bundle)
    write(root / "claim-graph-impact.json", report)
    return bundle, report


def run_earned_memory_proof(root: Path) -> dict[str, Any]:
    """Run the bounded two-generation interruption/inheritance prerequisite."""

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from openline_proof_adapter import PolicyConfig, ProofAdapter, public_key_hex as adapter_public_key_hex
    from olp_swarm_gate import (
        EvalAirlockAppraisal,
        ReceiverPromotionExecutor,
        ReceiverStateStore,
        SuccessorProposal,
        SuccessorPromotionGate,
        SuccessorPromotionPolicy,
        evaluator_key_fingerprint,
        materialize_appraisal_receipt,
        public_key_hex as evaluator_public_key_hex,
    )
    from olp_swarm_gate.promotion_ratchet import (
        ProductionEvidence,
        ProtectedDimension,
        evaluate_production_standing,
    )
    from olp_swarm_gate.rollback_recommendation import build_rollback_recommendation

    from .experiment import cases, evaluate, object_hash
    from .runtime import BASELINE, CANDIDATE, RULES

    root.mkdir(parents=True, exist_ok=False)

    # Tier-3/constitutional mutation negative control. The evaluator callback
    # must remain untouched because schema admission runs first.
    evaluator_calls = 0

    def forbidden_evaluator(_candidate: dict[str, Any]) -> None:
        nonlocal evaluator_calls
        evaluator_calls += 1

    attack = guarded_strategy_evaluation(
        {**CANDIDATE, "evaluator": "worker-owned"},
        forbidden_evaluator,
    )
    attack["evaluator_calls"] = evaluator_calls
    write(root / "constitutional-attack.json", attack)
    if attack["decision"] != "DENY" or evaluator_calls != 0:
        raise RuntimeError("constitutional_mutation_reached_evaluator")

    write(root / "incumbent.json", BASELINE)
    write(root / "candidate.json", CANDIDATE)
    write(
        root / "registration.json",
        {
            "experiment": EXPERIMENT_ID,
            "rules": RULES,
            "cases": cases(),
            "baseline_hash": file_hash(root / "incumbent.json"),
            "candidate_hash": file_hash(root / "candidate.json"),
            "minimum_gain": 0.25,
            "max_critical_failures": 0,
            "interruption_point": "after persisted PROMOTE decision, before receiver execution",
            "constitutional_mutation_surface": "strategy schema only; evaluator and policy fields forbidden",
        },
    )

    baseline = evaluate(BASELINE, root / "baseline")
    candidate_eval = evaluate(CANDIDATE, root / "candidate-evaluation")
    evaluation = {
        "baseline": baseline,
        "candidate": candidate_eval,
        "registration_sha256": file_hash(root / "registration.json"),
    }
    write(root / "evaluation.json", evaluation)

    evaluator_key = Ed25519PrivateKey.generate()
    evaluator_public_key = evaluator_public_key_hex(evaluator_key)
    now = time.time()
    policy = SuccessorPromotionPolicy(
        receipt_path=str(root / "promotion.jsonl"),
        appraisal_receipt_dir=str(root / "appraisals"),
        expected_evaluator_id="earned-memory-checker",
        expected_evaluator_hash=evaluator_key_fingerprint(evaluator_public_key),
        expected_evaluator_public_key=evaluator_public_key,
        expected_benchmark_id=EXPERIMENT_ID,
        expected_benchmark_version="1",
        expected_benchmark_owner="receiver",
        expected_heldout_set_hash=object_hash(cases()),
        expected_policy_hash=object_hash(RULES),
        min_heldout_delta=0.25,
        min_candidate_score=1.0,
        max_critical_failures=0,
        require_evaluation_artifact_hash=True,
        receiver_state_path=str(root / "receiver.json"),
        receiver_artifact_dir=str(root / "artifacts"),
    )
    write(root / "evaluator-public-key.json", {"public_key": evaluator_public_key})
    write(root / "promotion-policy.json", policy.frozen_public_dict())

    store = ReceiverStateStore(policy.receiver_state_path, policy.receiver_artifact_dir)
    store.initialize(
        version_id="source-limit-1",
        version_hash=file_hash(root / "incumbent.json"),
        now=now,
        artifact_path=root / "incumbent.json",
    )
    proposal = SuccessorProposal(
        "earned-memory-strategy-1",
        "strategy-proposer",
        "source-limit-1",
        file_hash(root / "incumbent.json"),
        "source-limit-8",
        file_hash(root / "candidate.json"),
        "Widen source coverage while preserving receiver-owned rules.",
        now,
    )
    appraisal = EvalAirlockAppraisal(
        "",
        policy.expected_evaluator_id,
        policy.expected_evaluator_hash,
        policy.expected_benchmark_id,
        policy.expected_benchmark_version,
        policy.expected_benchmark_owner,
        policy.expected_heldout_set_hash,
        policy.expected_policy_hash,
        object_hash(evaluation),
        proposal.source_version_hash,
        proposal.successor_version_hash,
        baseline["score"],
        candidate_eval["score"],
        candidate_eval["critical_failures"],
        True,
        "SUPPORTED",
        now,
        evaluation_artifact_hash=file_hash(root / "evaluation.json"),
    )
    appraisal = materialize_appraisal_receipt(
        appraisal,
        policy.appraisal_receipt_dir,
        signing_key=evaluator_key,
    )
    decision = SuccessorPromotionGate(policy).evaluate(
        proposal=proposal,
        appraisal=appraisal,
        now=now,
    )
    write(root / "decision.json", decision)
    if decision.get("decision") != "PROMOTE" or not decision.get("receipt_persisted"):
        raise RuntimeError("expected_persisted_promotion_decision")

    # Interruption: no ReceiverPromotionExecutor call yet.
    pre_state = store.read()
    write(root / "receiver-pre-promotion.json", pre_state)
    if pre_state["generation"] != 0 or _current_hash(pre_state) == proposal.successor_version_hash:
        raise RuntimeError("promotion_happened_before_interruption")

    adapter_key = Ed25519PrivateKey.generate()
    proof_adapter_public_key = adapter_public_key_hex(adapter_key)
    adapter = ProofAdapter(
        receipts_path=str(root / "boundary-receipts.jsonl"),
        signer_key=adapter_key,
        key_id=ADAPTER_KEY_ID,
        config=PolicyConfig(),
    )

    memory_candidate = project_memory(
        candidate_hash=proposal.successor_version_hash,
        decision=decision,
        receiver_state=pre_state,
        standing="ACTIVE",
    )
    write(root / "memory-phase-1-candidate.json", memory_candidate)
    append_jsonl(root / "verified-memory.jsonl", memory_candidate)
    _emit_memory_boundary(
        adapter,
        memory_candidate,
        "memory-phase-1",
        "PROMOTE decision exists but receiver execution has not completed.",
    )
    if memory_candidate["status"] != "candidate":
        raise RuntimeError("pre_promotion_memory_inherited")

    # Restart both state reader and Proof Adapter, then execute the exact
    # persisted promotion decision. No re-evaluation and no new authorization.
    store = ReceiverStateStore(policy.receiver_state_path, policy.receiver_artifact_dir)
    adapter = ProofAdapter(
        receipts_path=str(root / "boundary-receipts.jsonl"),
        signer_key=adapter_key,
        key_id=ADAPTER_KEY_ID,
        config=PolicyConfig(),
    )
    execution = ReceiverPromotionExecutor(
        decision_receipt_path=policy.receipt_path,
        state_store=store,
    ).execute(
        promotion_receipt=decision,
        candidate_artifact_path=root / "candidate.json",
        now=now + 1,
    )
    write(root / "promotion-execution.json", execution)
    post_state = store.read()
    write(root / "receiver-post-promotion.json", post_state)

    memory_inherited = project_memory(
        candidate_hash=proposal.successor_version_hash,
        decision=decision,
        receiver_state=post_state,
        standing="ACTIVE",
    )
    write(root / "memory-phase-2-inherited.json", memory_inherited)
    append_jsonl(root / "verified-memory.jsonl", memory_inherited)
    _emit_memory_boundary(
        adapter,
        memory_inherited,
        "memory-phase-2",
        "Restart recovered the existing receipt chain and exact receiver promotion completed.",
    )
    if memory_inherited["status"] != "inherited":
        raise RuntimeError("exact_promotion_failed_to_earn_inheritance")

    # The accepted lesson is supported by exact frozen evaluation + promotion.
    # Claim Graph is used only to compute what happens if that admitted support
    # later loses standing; it does not adjudicate truth.
    support_text = (
        "The exact source-limit-8 strategy passed the frozen receiver evaluation "
        "and completed the persisted receiver promotion."
    )
    _claim_inputs, impact = _claim_graph_reopen(root, support_text)
    quarantined_ids = {
        item["claim_id"]
        for item in impact["classifications"]["quarantine"]
    }
    decision_claim_ids = set(impact["decision_claim_ids_touched"])
    if not quarantined_ids or not decision_claim_ids or quarantined_ids != decision_claim_ids:
        raise RuntimeError("claim_graph_did_not_reopen_supporting_standing")

    production_evidence = {
        "utility_score": 0.0,
        "promoted_utility_floor": 1.0,
        "protected_dimensions": [
            {
                "name": "supporting_evidence_standing",
                "baseline": 1.0,
                "candidate": 0.0,
                "epsilon": 0.0,
                "direction": "higher_is_better",
            }
        ],
    }
    write(root / "post-promotion-standing-evidence.json", production_evidence)
    standing_receipt = evaluate_production_standing(
        ProductionEvidence(
            utility_score=production_evidence["utility_score"],
            promoted_utility_floor=production_evidence["promoted_utility_floor"],
            protected_dimensions=tuple(
                ProtectedDimension(**item)
                for item in production_evidence["protected_dimensions"]
            ),
        )
    )
    write(root / "standing-receipt.json", standing_receipt)
    if standing_receipt.get("decision") != "REOPEN":
        raise RuntimeError("standing_did_not_reopen")

    rollback = build_rollback_recommendation(
        standing_receipt=standing_receipt,
        receiver_state=store.read(),
    )
    write(root / "rollback-recommendation.json", rollback)
    if (
        rollback.get("recommendation") != "ROLLBACK_ELIGIBLE"
        or rollback.get("execution_authority") != "NONE"
        or rollback.get("auto_execute") is not False
    ):
        raise RuntimeError("rollback_recommendation_boundary_failed")

    # Deliberately do not call rollback_last. Reopened knowledge and installed
    # receiver state are separate. Persist the unchanged receiver state as proof.
    after_reopen_state = store.read()
    write(root / "receiver-after-reopen.json", after_reopen_state)
    if (
        after_reopen_state["generation"] != post_state["generation"]
        or _current_hash(after_reopen_state) != _current_hash(post_state)
    ):
        raise RuntimeError("memory_standing_mutated_installed_state")

    memory_questioned = project_memory(
        candidate_hash=proposal.successor_version_hash,
        decision=decision,
        receiver_state=after_reopen_state,
        standing="REOPEN",
        claim_report_id=impact["report_id"],
    )
    write(root / "memory-phase-3-questioned.json", memory_questioned)
    append_jsonl(root / "verified-memory.jsonl", memory_questioned)
    adapter = ProofAdapter(
        receipts_path=str(root / "boundary-receipts.jsonl"),
        signer_key=adapter_key,
        key_id=ADAPTER_KEY_ID,
        config=PolicyConfig(),
    )
    _emit_memory_boundary(
        adapter,
        memory_questioned,
        "memory-phase-3",
        "Supporting evidence lost admitted standing; receiver version remains installed pending separate recovery authority.",
    )

    generation_2 = generation_context([memory_questioned])
    write(root / "generation-2-context.json", generation_2)
    if generation_2["inherited"]:
        raise RuntimeError("reopened_lesson_leaked_into_inherited_generation_context")

    summary = {
        "experiment": EXPERIMENT_ID,
        "verdict": VERDICT,
        "phase_statuses": [
            memory_candidate["status"],
            memory_inherited["status"],
            memory_questioned["status"],
        ],
        "promotion_decision": decision["decision"],
        "receiver_generation": after_reopen_state["generation"],
        "installed_version_unchanged_after_reopen": (
            _current_hash(after_reopen_state) == proposal.successor_version_hash
        ),
        "claim_graph_classification": "QUARANTINE",
        "standing_decision": standing_receipt["decision"],
        "rollback_recommendation": rollback["recommendation"],
        "rollback_execution_authority": rollback["execution_authority"],
        "rollback_auto_execute": rollback["auto_execute"],
        "generation_2_inherited_count": len(generation_2["inherited"]),
        "generation_2_warning_count": len(generation_2["warnings"]),
        "constitutional_attack": attack["decision"],
        "constitutional_attack_evaluator_calls": evaluator_calls,
        "runtime_permission": "NONE",
        "evaluator_public_key": evaluator_public_key,
        "proof_adapter_public_key": proof_adapter_public_key,
        "proof_adapter_key_id": ADAPTER_KEY_ID,
    }
    write(root / "summary.json", summary)

    # Seal the closed proof directory with the receiver evaluator key. Verification
    # still requires the evaluator public key out-of-band; the embedded copy is
    # not a trust root.
    files = {
        path.relative_to(root).as_posix(): file_hash(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    seal_body = {
        "schema": "openline.research-swarm.earned-memory-proof.v1",
        "experiment": EXPERIMENT_ID,
        "files": files,
        "evaluator_public_key": evaluator_public_key,
        "proof_adapter_public_key": proof_adapter_public_key,
    }
    signature = evaluator_key.sign(dumps(seal_body)).hex()
    write(root / "experiment-seal.json", {"body": seal_body, "signature": signature})
    return summary


def verify_earned_memory_proof(
    root: Path,
    *,
    expected_evaluator_public_key: str,
    expected_proof_adapter_public_key: str,
) -> dict[str, Any]:
    """Independently recompute the evidence-derived inheritance lifecycle."""

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from openline_claim_graph import analyze_source_impact
    from openline_proof_adapter import ReceiptLog, verify_chain as verify_adapter_chain
    from olp_swarm_gate import (
        EvalAirlockAppraisal,
        verify_materialized_appraisal_receipt,
        verify_receiver_state_file,
        verify_chain as verify_promotion_chain,
    )
    from olp_swarm_gate.promotion_ratchet import (
        ProductionEvidence,
        ProtectedDimension,
        evaluate_production_standing,
    )

    from .experiment import evaluate

    seal = load(root / "experiment-seal.json")
    body = seal["body"]
    if body.get("experiment") != EXPERIMENT_ID:
        raise ValueError("experiment_id_mismatch")
    if body.get("evaluator_public_key") != expected_evaluator_public_key:
        raise ValueError("evaluator_key_mismatch")
    if body.get("proof_adapter_public_key") != expected_proof_adapter_public_key:
        raise ValueError("proof_adapter_key_mismatch")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(expected_evaluator_public_key)).verify(
        bytes.fromhex(seal["signature"]),
        dumps(body),
    )

    observed_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != root / "experiment-seal.json"
    }
    if observed_files != set(body["files"]):
        raise ValueError("proof_file_closure")
    for name, expected in body["files"].items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("proof_file_path_invalid")
        if file_hash(path) != expected:
            raise ValueError("proof_file_hash_mismatch")

    # Recompute the existing synthetic evaluator from the exact candidate and
    # baseline artifacts. This does not trust the saved score.
    with tempfile.TemporaryDirectory() as td:
        replay_root = Path(td)
        baseline_replay = evaluate(load(root / "incumbent.json"), replay_root / "baseline")
        candidate_replay = evaluate(load(root / "candidate.json"), replay_root / "candidate")
    saved_evaluation = load(root / "evaluation.json")
    for lane, replay in (("baseline", baseline_replay), ("candidate", candidate_replay)):
        saved = saved_evaluation[lane]
        for key in ("score", "critical_failures", "cases_sha256", "rules_sha256", "strategy_sha256"):
            if saved[key] != replay[key]:
                raise ValueError("evaluation_recompute_mismatch")

    appraisal_files = sorted((root / "appraisals").glob("*.json"))
    if len(appraisal_files) != 1:
        raise ValueError("appraisal_count")
    appraisal_doc = load(appraisal_files[0])
    appraisal = EvalAirlockAppraisal(
        appraisal_receipt_hash=appraisal_files[0].stem,
        **appraisal_doc["appraisal"],
    )
    appraisal_errors = verify_materialized_appraisal_receipt(
        appraisal,
        root / "appraisals",
        expected_public_key=expected_evaluator_public_key,
    )
    if appraisal_errors:
        raise ValueError("appraisal_signature:" + ",".join(appraisal_errors))
    if appraisal.evaluation_artifact_hash != file_hash(root / "evaluation.json"):
        raise ValueError("appraisal_evaluation_binding")

    promotion_chain = verify_promotion_chain(str(root / "promotion.jsonl"))
    if not promotion_chain["valid"]:
        raise ValueError("promotion_chain")
    state_check = verify_receiver_state_file(root / "receiver.json")
    if not state_check["valid"]:
        raise ValueError("receiver_state")

    receipts = ReceiptLog(str(root / "boundary-receipts.jsonl")).load()
    if not verify_adapter_chain(
        receipts,
        public_key=expected_proof_adapter_public_key,
        key_id=ADAPTER_KEY_ID,
    ):
        raise ValueError("proof_adapter_chain")
    if len(receipts) != 3:
        raise ValueError("proof_adapter_receipt_count")

    decision = load(root / "decision.json")
    pre_state = load(root / "receiver-pre-promotion.json")
    post_state = load(root / "receiver-post-promotion.json")
    after_reopen = load(root / "receiver-after-reopen.json")
    candidate_hash = file_hash(root / "candidate.json")

    expected_phase_1 = project_memory(
        candidate_hash=candidate_hash,
        decision=decision,
        receiver_state=pre_state,
        standing="ACTIVE",
    )
    expected_phase_2 = project_memory(
        candidate_hash=candidate_hash,
        decision=decision,
        receiver_state=post_state,
        standing="ACTIVE",
    )

    graph_inputs = load(root / "claim-graph-inputs.json")
    report = analyze_source_impact(
        graph_inputs["snapshot"],
        graph_inputs["sources"],
        graph_inputs["event"],
        graph_inputs["policy"],
    )
    if dumps(report) != dumps(load(root / "claim-graph-impact.json")):
        raise ValueError("claim_graph_recompute_mismatch")
    claim_id = graph_inputs["claim"]["claim_id"]
    quarantined = {item["claim_id"] for item in report["classifications"]["quarantine"]}
    if claim_id not in quarantined or claim_id not in set(report["decision_claim_ids_touched"]):
        raise ValueError("claim_graph_standing_not_reopened")

    standing_evidence = load(root / "post-promotion-standing-evidence.json")
    expected_standing = evaluate_production_standing(
        ProductionEvidence(
            utility_score=standing_evidence["utility_score"],
            promoted_utility_floor=standing_evidence["promoted_utility_floor"],
            protected_dimensions=tuple(
                ProtectedDimension(**item)
                for item in standing_evidence["protected_dimensions"]
            ),
        )
    )
    if dumps(expected_standing) != dumps(load(root / "standing-receipt.json")):
        raise ValueError("standing_recompute_mismatch")
    if expected_standing["decision"] != "REOPEN":
        raise ValueError("standing_not_reopened")

    expected_phase_3 = project_memory(
        candidate_hash=candidate_hash,
        decision=decision,
        receiver_state=after_reopen,
        standing="REOPEN",
        claim_report_id=report["report_id"],
    )
    phases = [
        load(root / "memory-phase-1-candidate.json"),
        load(root / "memory-phase-2-inherited.json"),
        load(root / "memory-phase-3-questioned.json"),
    ]
    if [dumps(item) for item in phases] != [
        dumps(expected_phase_1),
        dumps(expected_phase_2),
        dumps(expected_phase_3),
    ]:
        raise ValueError("memory_projection_mismatch")
    if [item["status"] for item in phases] != ["candidate", "inherited", "questioned"]:
        raise ValueError("memory_phase_sequence")

    lines = [json.loads(line) for line in (root / "verified-memory.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if [dumps(item) for item in lines] != [dumps(item) for item in phases]:
        raise ValueError("verified_memory_jsonl_mismatch")

    generation_2 = generation_context([expected_phase_3])
    if dumps(generation_2) != dumps(load(root / "generation-2-context.json")):
        raise ValueError("generation_2_context_mismatch")
    if generation_2["inherited"] or len(generation_2["warnings"]) != 1:
        raise ValueError("questioned_memory_reused_as_inherited")

    if pre_state["generation"] != 0 or _current_hash(pre_state) == candidate_hash:
        raise ValueError("interruption_boundary_failed")
    if post_state["generation"] != 1 or _current_hash(post_state) != candidate_hash:
        raise ValueError("promotion_boundary_failed")
    if (
        after_reopen["generation"] != post_state["generation"]
        or _current_hash(after_reopen) != _current_hash(post_state)
    ):
        raise ValueError("reopen_silently_changed_installed_version")

    rollback = load(root / "rollback-recommendation.json")
    last_transition = after_reopen["transitions"][-1]
    if (
        rollback.get("recommendation") != "ROLLBACK_ELIGIBLE"
        or rollback.get("execution_authority") != "NONE"
        or rollback.get("auto_execute") is not False
        or rollback.get("current_version_hash") != candidate_hash
        or rollback.get("receiver_state_generation") != after_reopen["generation"]
        or rollback.get("receiver_state_hash") != after_reopen["state_hash"]
        or rollback.get("bound_transition_hash") != last_transition["transition_hash"]
    ):
        raise ValueError("rollback_recommendation_binding")

    attack = load(root / "constitutional-attack.json")
    if (
        attack.get("decision") != "DENY"
        or attack.get("reason") != "CONSTITUTIONAL_MUTATION_DENIED"
        or attack.get("evaluator_calls") != 0
        or attack.get("evaluator_called") is not False
    ):
        raise ValueError("constitutional_attack_boundary")

    summary = load(root / "summary.json")
    expected_summary_facts = {
        "verdict": VERDICT,
        "phase_statuses": ["candidate", "inherited", "questioned"],
        "receiver_generation": 1,
        "generation_2_inherited_count": 0,
        "rollback_execution_authority": "NONE",
        "rollback_auto_execute": False,
        "constitutional_attack_evaluator_calls": 0,
    }
    for key, expected in expected_summary_facts.items():
        if summary.get(key) != expected:
            raise ValueError(f"summary_mismatch:{key}")

    return {
        "verified": True,
        "experiment": EXPERIMENT_ID,
        "verdict": VERDICT,
        "phase_statuses": ["candidate", "inherited", "questioned"],
        "receiver_generation": 1,
        "claim_graph_recomputed": True,
        "evaluation_recomputed": True,
        "proof_adapter_receipts": len(receipts),
        "installed_version_unchanged_after_reopen": True,
        "constitutional_attack_evaluator_calls": 0,
    }
