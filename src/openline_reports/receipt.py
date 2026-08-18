from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from .canonical import sha256_obj

@dataclass
class ResearchHandoff:
    schema: str
    investigation_id: str
    disposition: str
    investigation_hash: str
    created_at: str
    authority: str
    reopened_from_hash: str = ""
    notes: str = ""

def make_handoff(investigation: dict[str, Any], *, notes: str = "") -> dict[str, Any]:
    disposition = investigation.get("disposition")
    if disposition is None:
        raise ValueError("handoff requires a disposition")
    return asdict(ResearchHandoff(
        schema="openline.research.handoff.v1",
        investigation_id=investigation["investigation_id"],
        disposition=disposition,
        investigation_hash=sha256_obj(investigation),
        created_at=datetime.now(timezone.utc).isoformat(),
        authority="research_handoff_only",
        reopened_from_hash=investigation.get("reopened_from_hash", ""),
        notes=notes,
    ))
