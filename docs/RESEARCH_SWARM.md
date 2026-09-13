# RESEARCH-SWARM-001

**Maturity: research integration.** Three worker roles hand off checked source assertions through OpenLine Lite. A receiver evaluates a proposed source-selection strategy, signs an appraisal, and uses Swarm Improvement Gate to install the exact candidate only when it passes. The next job uses the installed artifact.

This is a working, deliberately narrow foundation for a research swarm. The supplied experiment uses deterministic worker fixtures, not live LLMs. It does not demonstrate autonomous scientific discovery or general self-improvement.

## Run it

From the `openline-reports` repository root, on Linux with Python 3.11 or newer:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e . -r requirements-swarm.txt
python -m openline_reports.swarm.experiment demo --out /tmp/research-swarm-001
```

Use a fresh output directory. The command prints a summary and evaluator public key. Copy that key into verification:

```sh
python -m openline_reports.swarm.experiment verify-demo \
  --out /tmp/research-swarm-001 --public-key YOUR_RECORDED_KEY
python scripts/release_check.py
```

Keep the key separately from evidence received from another party. Reading a key out of an untrusted bundle and trusting it only proves self-consistency. The demo generates ephemeral signing keys in memory; it saves public keys, never private keys. Production evaluator identity and key custody are outside this experiment.

Expected fixture result: incumbent 2/4 correct, candidate 4/4, `PROMOTE`, receiver generation 1, and the next job uses the candidate. These four cases are public synthetic controls, not unseen research tasks. The upstream appraisal field named `heldout_set_hash` carries their hash; that field name does not make this a held-out evaluation.

## What runs

1. **Proposer:** extracts assertions from an owner-supplied JSON source snapshot.
2. **Critic:** receives checked assertions and can preserve objections.
3. **Synthesizer:** returns the receiver's supported or unresolved result. It cannot erase missing coverage, source disagreement, or objections.

Each role's handoff uses Lite's actual model-handoff verifier, source hashes, and JSON pointers. Only exact source assertions enter verified state. Reports validates the resulting investigation and creates a research handoff. `supported` means the active snapshot assertions agree with complete coverage; it does not mean the underlying sources are true. Questioned and withdrawn sources cannot supply active support.

The three roles run sequentially because each consumes the previous checked state. There is no concurrent swarm scheduler, hidden COLE dependency, or universal coherence score. Their epistemic division is propose, challenge, and synthesize under receiver-owned rules.

## What can improve

A fourth, separate strategy-proposer can change only `source_limit`, an integer from 1 to 8. It cannot alter the source corpus, evaluator, role count, acceptance rules, or signing keys. The default fixture proposes checking all eight allowed sources rather than one.

Both strategies run on the same four cases: agreement, disagreement, withdrawn evidence, and agreement across three sources. The registration is frozen before either lane runs. Acceptance requires 100% fixture correctness, at least 0.25 improvement, and no incorrect supported answer. Missing evidence must remain unresolved.

The evaluator binds scores to the exact strategy and evidence hashes, then signs the upstream gate's appraisal. The existing gate decides; its executor performs the receiver-state compare-and-swap. An unchanged candidate is quarantined; insufficient improvement is rejected. Neither changes the incumbent. A promotion cannot be replayed to increment the generation again.

This replaces a bounded research strategy, not model weights or arbitrary code. Research output retains `runtime_permission: NONE`; a strategy promotion grants no permission to spend, send, deploy, or execute research recommendations.

## Use your own source pack

Save `pack.json`:

```json
{
  "id": "limit-check",
  "question": "What limit do the active snapshots report?",
  "pointer": "/limit",
  "sources": [
    {"id": "a", "locator": "owner-snapshot:a", "standing": "active", "data": {"limit": 12}},
    {"id": "b", "locator": "owner-snapshot:b", "standing": "active", "data": {"limit": 12}}
  ]
}
```

Save `strategy.json`:

```json
{"schema":"research.swarm.strategy.v1","source_limit":8}
```

```sh
python -m openline_reports.swarm.experiment run \
  --pack pack.json --strategy strategy.json --out /tmp/research-job
```

This profile compares one JSON pointer resolving to a scalar (string, integer, boolean, or null) in at most eight sources. It does not browse or extract claims from arbitrary prose. Source standing is supplied by the owner, not independently discovered. A later source change requires a new run; there is no background monitoring here.

## Connect real workers

Provide a **trusted executable bridge** that reads one JSON request from stdin and returns one JSON object on stdout:

```sh
python -m openline_reports.swarm.experiment run \
  --pack pack.json --strategy strategy.json --out /tmp/live-research-job \
  --agent-command '["/absolute/path/to/your-bridge"]'
```

Requests include `role` and `verified_context`, plus the role-specific fields:

| Role | Additional request fields | Exact response shape |
|---|---|---|
| proposer | question, pointer, sources | `{"findings":[{"source_id":"a","value":12}]}` |
| critic | question, instruction | `{"objections":[]}` or nonempty objection strings |
| synthesizer | question, receiver_result, unresolved | `{"status":"supported","answer":12}` or the exact unresolved result |

The bridge can route each role to a different provider. No provider SDK or credentials are bundled. The CLI performs at most three role calls, no retries, with a 30-second timeout per bridge call and a 256 KiB output cap. These are call/time/output limits, **not a dollar or token budget**. The bridge must enforce its provider spending limits.

An optional `demo --strategy-command '["/absolute/path/to/your-bridge"]'` asks a real bridge for the candidate strategy. Its role is `strategy-proposer`; it receives baseline, receiver_rules, and task, and must return the exact strategy schema above. Evaluation lanes still use deterministic fixture workers. This is not evidence that a live multi-provider swarm has improved.

**Security boundary:** the subprocess adapter uses a temporary working directory, no shell, process-group termination, and Unix output limits. This is not a sandbox. It inherits the launching environment. A trusted bridge must keep model-controlled tools in a separate security principal away from receiver files, source snapshots, evaluator code, and secrets. In-process callbacks are trusted test fixtures. Merely installing this package cannot secure an arbitrary tool-enabled agent on the same host.

## Evidence and verification

A job archives requests, responses, the source snapshot, rules, strategy, Lite transitions, Reports investigation, research handoff, result, and a signed file manifest. A quarantined run can lack later stages. `verify` checks the pinned signing key, exact file set, artifact hashes, and replays Lite transitions.

The experiment additionally preserves the registration, both evaluation lanes, signed appraisal, gate decision chain, receiver history, installed artifacts, next job, and an experiment-wide signed seal. `verify-demo` checks these bindings and recomputes fixture evaluation from the installed code. This requires trusting the checker and its pinned dependencies. A signature authenticates evidence; it does not prove a claim about the world.

Tests cover evidence mutation, wrong signing key, extra files, false assertions, missing and withdrawn sources, unresolved disagreements, attempted synthesis overrides, unauthorized strategy fields, unchanged candidates, promotion replay, adapter timeout, excessive output, and an actual JSON subprocess bridge.

The optional CI installs pinned Lite/Gate revisions and runs the full Reports release check plus a fresh experiment and verification. The base Reports install remains usable without swarm dependencies; swarm tests explicitly skip when those dependencies are absent.
