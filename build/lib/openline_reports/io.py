from __future__ import annotations
import json
from pathlib import Path
from .model import Investigation, SourceRef, Claim, Objection

def load(path: str | Path) -> Investigation:
    d = json.loads(Path(path).read_text())
    if not isinstance(d, dict):
        raise ValueError("investigation JSON must be an object")
    return Investigation(
        investigation_id=d["investigation_id"],
        title=d["title"],
        question=d["question"],
        initial_hypothesis=d["initial_hypothesis"],
        sources=[SourceRef(**x) for x in d.get("sources", [])],
        claims=[Claim(**x) for x in d.get("claims", [])],
        objections=[Objection(**x) for x in d.get("objections", [])],
        discovery_delta=d.get("discovery_delta", ""),
        result_summary=d.get("result_summary", ""),
        disposition=d.get("disposition"),
        disposition_reason=d.get("disposition_reason", ""),
        reopened_from_hash=d.get("reopened_from_hash", ""),
    )

def save(inv: Investigation, path: str | Path) -> None:
    Path(path).write_text(json.dumps(inv.to_dict(), indent=2, ensure_ascii=False) + "\n")
