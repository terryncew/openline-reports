# Research Contract

## 1. Starting state

Every investigation records a question and an initial hypothesis before the result is known.

The hypothesis is not evidence.

## 2. Evidence custody

Each material claim records the sources or admitted claim basis supporting it.

Source presence alone does not prove support. Source standing is mechanically enforced:

- `active` may directly support a claim;
- `questioned` remains visible but cannot be the sole direct basis of a supported claim;
- `withdrawn` remains visible but cannot directly support a claim.

Supported, unsupported, unresolved, and withdrawn claims remain distinguishable at runtime.

A supported claim may depend on other supported claims. Declared dependencies are required, must exist, and must form an acyclic graph. If a required dependency is no longer supported, the downstream claim cannot remain mechanically valid as supported without re-adjudication.

## 3. Competing explanations

Contested interpretations and causal claims may preserve alternatives.

Alternative references must resolve to real claim IDs. The harness validates custody of the relation; it does not infer semantic equivalence or decide that one alternative defeats another.

Routine uncontested facts do not require artificial counterclaims.

## 4. Objections, not grades

Review stages preserve concrete objections tied to a real claim or source. An objection cannot target an invented object.

Resolved objections require an explicit resolution. Candidate handoffs cannot retain unresolved objections.

## 5. Discovery delta

A surviving handoff records what changed between the starting hypothesis and the resulting understanding.

If repeated investigations always return the initial thesis unchanged, treat that as a warning of confirmation bias rather than proof of consistency.

## 6. Outcomes

- `kill`: the evidence does not support a useful research result.
- `pivot`: something survived, but it is materially different from the starting hypothesis.
- `candidate`: a bounded result survived and is worth handing downstream.

A handoff requires one of these dispositions. Invalid runtime values fail closed.

A candidate also requires nonempty sources, nonempty claims, and at least one supported claim with a valid active basis. Unsupported or withdrawn claims cannot remain inside a candidate state.

These outcomes do not authorize downstream action.

## 7. Corrections and reopen lineage

Later evidence may change the standing of a source or claim.

A reopened investigation records the SHA-256 hash of the complete prior investigation state. Handoff of a reopened investigation requires the caller to supply that prior state, and the hash must match exactly.

This verifies lineage to the supplied prior artifact. It does not establish external timestamping, completeness of global history, or truth of the prior state.

The prior record is preserved rather than silently overwritten.
