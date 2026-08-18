from __future__ import annotations
import re
from .model import (
    Investigation,
    VALID_CLAIM_STATUSES,
    VALID_SOURCE_STANDINGS,
    VALID_DISPOSITIONS,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _dependency_cycles(inv: Investigation) -> list[list[str]]:
    graph = {c.claim_id: list(c.depends_on) for c in inv.claims}
    seen: set[str] = set()
    active: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        if node in active:
            try:
                i = stack.index(node)
                cycles.append(stack[i:] + [node])
            except ValueError:
                cycles.append([node, node])
            return
        if node in seen:
            return
        seen.add(node)
        active.add(node)
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt in graph:
                visit(nxt)
        stack.pop()
        active.remove(node)

    for node in graph:
        visit(node)
    return cycles


def validate_investigation(inv: Investigation, *, require_disposition: bool = False) -> list[str]:
    errors: list[str] = []

    if not isinstance(inv.investigation_id, str) or not inv.investigation_id.strip():
        errors.append("investigation_id_required")
    if not isinstance(inv.title, str) or not inv.title.strip():
        errors.append("title_required")
    if not isinstance(inv.question, str) or not inv.question.strip():
        errors.append("question_required")
    if not isinstance(inv.initial_hypothesis, str) or not inv.initial_hypothesis.strip():
        errors.append("initial_hypothesis_required")

    if inv.disposition is not None and inv.disposition not in VALID_DISPOSITIONS:
        errors.append(f"invalid_disposition:{inv.disposition}")
    if require_disposition and inv.disposition is None:
        errors.append("disposition_required_for_handoff")

    if inv.reopened_from_hash:
        if not isinstance(inv.reopened_from_hash, str) or not _SHA256_RE.fullmatch(inv.reopened_from_hash):
            errors.append("invalid_reopened_from_hash")

    source_ids = [s.source_id for s in inv.sources]
    claim_ids = [c.claim_id for c in inv.claims]
    source_id_set = set(source_ids)
    claim_id_set = set(claim_ids)

    if len(source_id_set) != len(source_ids):
        errors.append("duplicate_source_id")
    if len(claim_id_set) != len(claim_ids):
        errors.append("duplicate_claim_id")

    source_by_id = {s.source_id: s for s in inv.sources}
    claim_by_id = {c.claim_id: c for c in inv.claims}

    for s in inv.sources:
        if not isinstance(s.source_id, str) or not s.source_id.strip():
            errors.append("source_id_required")
        if not isinstance(s.title, str) or not s.title.strip():
            errors.append(f"source_title_required:{s.source_id}")
        if not isinstance(s.locator, str) or not s.locator.strip():
            errors.append(f"source_locator_required:{s.source_id}")
        if s.standing not in VALID_SOURCE_STANDINGS:
            errors.append(f"invalid_source_standing:{s.source_id}:{s.standing}")
        if not isinstance(s.primary, bool):
            errors.append(f"invalid_source_primary:{s.source_id}")

    for c in inv.claims:
        if not isinstance(c.claim_id, str) or not c.claim_id.strip():
            errors.append("claim_id_required")
        if not isinstance(c.text, str) or not c.text.strip():
            errors.append(f"claim_text_required:{c.claim_id}")
        if c.status not in VALID_CLAIM_STATUSES:
            errors.append(f"invalid_claim_status:{c.claim_id}:{c.status}")
            continue

        missing_sources = [sid for sid in c.source_ids if sid not in source_id_set]
        if missing_sources:
            errors.append(f"missing_source_refs:{c.claim_id}:" + ",".join(missing_sources))

        missing_claims = [cid for cid in c.depends_on if cid not in claim_id_set]
        if missing_claims:
            errors.append(f"missing_claim_dependencies:{c.claim_id}:" + ",".join(missing_claims))

        missing_alternatives = [cid for cid in c.alternatives if cid not in claim_id_set]
        if missing_alternatives:
            errors.append(f"missing_claim_alternatives:{c.claim_id}:" + ",".join(missing_alternatives))

        if c.claim_id in c.depends_on:
            errors.append(f"self_dependency:{c.claim_id}")
        if c.claim_id in c.alternatives:
            errors.append(f"self_alternative:{c.claim_id}")

        if c.status == "unresolved" and not isinstance(c.uncertainty, str):
            errors.append(f"invalid_uncertainty:{c.claim_id}")
        elif c.status == "unresolved" and not c.uncertainty.strip():
            errors.append(f"unresolved_claim_missing_uncertainty:{c.claim_id}")

        if c.status == "supported" and not c.source_ids and not c.depends_on:
            errors.append(f"supported_claim_without_basis:{c.claim_id}")

    for cycle in _dependency_cycles(inv):
        errors.append("dependency_cycle:" + "->".join(cycle))

    # Standing-aware support: a supported claim must have at least one active
    # direct source OR supported dependencies, and every declared dependency
    # must itself be a valid supported claim. Questioned/withdrawn sources
    # cannot be the sole direct basis.
    for c in inv.claims:
        if c.status != "supported":
            continue

        active_direct = any(
            sid in source_by_id and source_by_id[sid].standing == "active"
            for sid in c.source_ids
        )

        dependency_basis = bool(c.depends_on)
        dependencies_valid = True
        for dep_id in c.depends_on:
            dep = claim_by_id.get(dep_id)
            if dep is None:
                dependencies_valid = False
                continue
            if dep.status != "supported":
                dependencies_valid = False
                errors.append(
                    f"supported_claim_depends_on_non_supported:{c.claim_id}:{dep_id}:{dep.status}"
                )

        if c.depends_on and not dependencies_valid:
            errors.append(f"supported_claim_invalid_dependency_basis:{c.claim_id}")

        if not active_direct and not (dependency_basis and dependencies_valid):
            errors.append(f"supported_claim_without_active_basis:{c.claim_id}")

    objection_ids = [o.objection_id for o in inv.objections]
    if len(set(objection_ids)) != len(objection_ids):
        errors.append("duplicate_objection_id")

    valid_objection_targets = source_id_set | claim_id_set
    for o in inv.objections:
        if not isinstance(o.objection_id, str) or not o.objection_id.strip():
            errors.append("objection_id_required")
        if o.target not in valid_objection_targets:
            errors.append(f"invalid_objection_target:{o.objection_id}:{o.target}")
        if not isinstance(o.text, str) or not o.text.strip():
            errors.append(f"objection_text_required:{o.objection_id}")
        if not isinstance(o.basis, str) or not o.basis.strip():
            errors.append(f"objection_basis_required:{o.objection_id}")
        if not isinstance(o.resolved, bool):
            errors.append(f"invalid_objection_resolved:{o.objection_id}")
        if o.resolved and (not isinstance(o.resolution, str) or not o.resolution.strip()):
            errors.append(f"resolved_objection_missing_resolution:{o.objection_id}")

    if inv.disposition in ("pivot", "candidate"):
        if not isinstance(inv.discovery_delta, str) or not inv.discovery_delta.strip():
            errors.append("discovery_delta_required")
        if not isinstance(inv.result_summary, str) or not inv.result_summary.strip():
            errors.append("result_summary_required")

    if inv.disposition == "candidate":
        if not inv.sources:
            errors.append("candidate_requires_sources")
        if not inv.claims:
            errors.append("candidate_requires_claims")

        supported = [c.claim_id for c in inv.claims if c.status == "supported"]
        if not supported:
            errors.append("candidate_requires_supported_claim")

        unsupported = [c.claim_id for c in inv.claims if c.status == "unsupported"]
        if unsupported:
            errors.append("unsupported_claims_present:" + ",".join(unsupported))

        withdrawn = [c.claim_id for c in inv.claims if c.status == "withdrawn"]
        if withdrawn:
            errors.append("withdrawn_claims_present:" + ",".join(withdrawn))

        unresolved_objections = [o.objection_id for o in inv.objections if not o.resolved]
        if unresolved_objections:
            errors.append("unresolved_objections_present:" + ",".join(unresolved_objections))

    if inv.disposition == "kill" and (
        not isinstance(inv.disposition_reason, str) or not inv.disposition_reason.strip()
    ):
        errors.append("kill_reason_required")

    return errors
