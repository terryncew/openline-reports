# OpenLine Reports

OpenLine Reports is a generic research harness for turning a question, claim, source set, or artifact into a bounded research handoff.

It is not a publishing system, a writing model, or a truth score.

Its job is simple:

> Give it something you think is true. It preserves the starting hypothesis, tracks what the evidence supports, records objections and uncertainty, and returns what survived.

## Core workflow

```text
input / question
      ↓
initial hypothesis
      ↓
evidence collection
      ↓
competing explanations
      ↓
claim + basis graph
      ↓
objections / unresolved points
      ↓
discovery delta
      ↓
KILL / PIVOT / CANDIDATE
```

`CANDIDATE` means the investigation produced a bounded result worth handing back to the caller. It does not mean publish, deploy, invest, prescribe, or otherwise act. The downstream user or system owns that decision.

## What the gate actually enforces

A candidate handoff fails closed when:

- no disposition is present;
- runtime enum values are invalid;
- there are no sources, no claims, or no supported claim;
- a supported claim has no active direct basis and no valid supported dependency basis;
- a declared dependency is missing, non-supported, self-referential, or cyclic;
- an alternative points to a missing claim;
- an objection targets a missing claim/source;
- unresolved objections remain;
- unsupported or withdrawn claims remain in a candidate;
- an unresolved claim omits its uncertainty;
- reopen lineage is malformed or cannot be verified against the supplied prior investigation.

`typing.Literal` annotations are documentation only; the validator performs explicit runtime checks.

## Source standing

Sources have one of three runtime-enforced states:

- `active`: may serve as direct support;
- `questioned`: remains in the record but cannot be the sole direct basis of a supported claim;
- `withdrawn`: remains in the record but cannot serve as direct support.

A supported claim may also depend on other supported claims. Every declared dependency is treated as required. If a required dependency loses supported standing, the downstream supported claim fails validation until it is re-adjudicated.

## Reopening and correction lineage

A reopened investigation carries the SHA-256 hash of the complete prior investigation state.

Create a reopen:

```bash
openline-reports reopen prior.json --out reopened.json
```

A handoff for a reopened investigation must receive the exact prior investigation:

```bash
openline-reports handoff reopened.json \
  --prior prior.json \
  --out handoff.json
```

If the supplied prior state does not hash to `reopened_from_hash`, handoff fails closed.

This proves file-level lineage to the supplied prior state. It does not prove that the prior file was externally timestamped or that no other history exists.

## Design rules

- Evidence and prose are separate concerns.
- A starting hypothesis has no privileged standing.
- A claim cannot become stronger because it is rhetorically useful.
- Unresolved uncertainty stays unresolved.
- Reviewers produce objections, not self-issued approval scores.
- New claims discovered during synthesis must return to evidence review.
- The harness may return no result worth using.
- Corrections and later evidence should reopen affected claims instead of silently rewriting history.
- No universal credibility, originality, truth, or quality score is produced.

## Quick start

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/hostile_contract_probe.py
python scripts/release_check.py
```

Create an investigation:

```bash
openline-reports init \
  --id case-001 \
  --title "Example investigation" \
  --question "What actually happened?" \
  --hypothesis "The initial explanation is correct." \
  --out case.json
```

Validate a research state:

```bash
openline-reports check case.json
```

Create a handoff receipt bound to the deterministic investigation hash:

```bash
openline-reports handoff case.json --out handoff.json
```

The investigation hash is deterministic for identical investigation content. The handoff receipt itself contains `created_at` and is therefore not byte-for-byte deterministic across runs.

## What belongs above this repo

A newsroom can turn a `CANDIDATE` into an article.
A lab can turn it into an experiment proposal.
An investor can turn it into a thesis review.
A policy team can turn it into a decision memo.

Those applications provide their own final-use rules. This repository does not certify those downstream decisions.

## Status

v0.2.1 is a contract-hardening release. It makes source standing, dependency structure, alternative references, objection targets, runtime enums, disposition, and reopen lineage mechanically enforceable rather than merely representational.

## Bounded research swarm

[RESEARCH-SWARM-001](docs/RESEARCH_SWARM.md) connects three research roles through verified Lite handoffs and evaluates a proposed strategy before the existing Swarm Improvement Gate installs it. Includes a runnable offline experiment, signed evidence, adversarial tests, and a JSON bridge for external workers. Research integration; no live-model improvement claim.
