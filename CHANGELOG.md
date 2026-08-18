# Changelog

## 0.2.1

Contract-hardening release after hostile validation of v0.2.0.

- Enforce runtime values for source standing, claim status, and disposition.
- Require evidence-bearing `candidate` states: sources, claims, and at least one supported claim.
- Make source standing operational: questioned/withdrawn sources cannot be the sole direct basis of support.
- Propagate required dependency standing: supported claims cannot depend on non-supported claims.
- Reject missing/self alternative references and dependency cycles.
- Reject objections targeting nonexistent claims or sources.
- Require a disposition before a research handoff can be issued.
- Add verifiable reopen lineage: reopened investigations bind the prior investigation hash and handoff requires the exact prior artifact.
- Correct README wording: the investigation hash is deterministic; timestamped handoff receipts are not.
- Add hostile contract probes covering the v0.2.0 bypasses.

## 0.2.0

- Recast the core as a generic research handoff harness rather than a publication workflow.
- Remove personal style, editorial voice, and publication-certification concepts from the core package.
- Replace `published` with bounded research outcomes: `kill`, `pivot`, and `candidate`.
- Replace the prior approval artifact with a research handoff explicitly carrying no downstream authority.
- Add source standing, claim alternatives, dependency validation, objection resolution, and reopen lineage.
- Require discovery delta and result summary for surviving investigations.
- Add generic research and integration contracts.

## 0.1.0

- Initial publication-oriented prototype.
