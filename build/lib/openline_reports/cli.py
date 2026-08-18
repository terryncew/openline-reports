from __future__ import annotations
import argparse, json
from pathlib import Path
from .model import Investigation
from .io import load, save
from .gate import validate_investigation
from .receipt import make_handoff
from .canonical import sha256_obj

def cmd_init(args):
    inv = Investigation(
        investigation_id=args.id,
        title=args.title,
        question=args.question,
        initial_hypothesis=args.hypothesis,
    )
    save(inv, args.out)
    print(args.out)

def cmd_check(args):
    inv = load(args.file)
    errors = validate_investigation(inv)
    print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    raise SystemExit(0 if not errors else 1)

def cmd_reopen(args):
    prior = load(args.prior)
    prior_errors = validate_investigation(prior, require_disposition=True)
    if prior_errors:
        raise SystemExit("cannot reopen invalid prior investigation: " + "; ".join(prior_errors))
    d = prior.to_dict()
    prior_hash = sha256_obj(d)
    reopened = Investigation(
        investigation_id=args.id or prior.investigation_id,
        title=prior.title,
        question=prior.question,
        initial_hypothesis=prior.initial_hypothesis,
        sources=prior.sources,
        claims=prior.claims,
        objections=prior.objections,
        discovery_delta="",
        result_summary="",
        disposition=None,
        disposition_reason="",
        reopened_from_hash=prior_hash,
    )
    save(reopened, args.out)
    print(args.out)

def _verify_reopen_lineage(inv: Investigation, prior_path: str | None) -> list[str]:
    errors: list[str] = []
    if inv.reopened_from_hash:
        if not prior_path:
            return ["prior_required_for_reopened_investigation"]
        prior = load(prior_path)
        prior_errors = validate_investigation(prior, require_disposition=True)
        if prior_errors:
            return ["prior_investigation_invalid:" + ",".join(prior_errors)]
        actual = sha256_obj(prior.to_dict())
        if actual != inv.reopened_from_hash:
            errors.append("reopened_from_hash_mismatch")
    elif prior_path:
        errors.append("prior_supplied_but_no_reopened_from_hash")
    return errors

def cmd_handoff(args):
    inv = load(args.file)
    errors = validate_investigation(inv, require_disposition=True)
    errors.extend(_verify_reopen_lineage(inv, args.prior))
    if errors:
        raise SystemExit("cannot issue handoff: " + "; ".join(errors))
    receipt = make_handoff(inv.to_dict(), notes=args.notes)
    Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
    print(args.out)

def main():
    p = argparse.ArgumentParser(prog="openline-reports")
    sub = p.add_subparsers(required=True)

    a = sub.add_parser("init")
    a.add_argument("--id", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--question", required=True)
    a.add_argument("--hypothesis", required=True)
    a.add_argument("--out", required=True)
    a.set_defaults(func=cmd_init)

    a = sub.add_parser("check")
    a.add_argument("file")
    a.set_defaults(func=cmd_check)

    a = sub.add_parser("reopen")
    a.add_argument("prior")
    a.add_argument("--id")
    a.add_argument("--out", required=True)
    a.set_defaults(func=cmd_reopen)

    a = sub.add_parser("handoff")
    a.add_argument("file")
    a.add_argument("--out", required=True)
    a.add_argument("--prior")
    a.add_argument("--notes", default="")
    a.set_defaults(func=cmd_handoff)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
