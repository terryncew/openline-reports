from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Literal, Optional

ClaimStatus = Literal["supported", "unsupported", "unresolved", "withdrawn"]
SourceStanding = Literal["active", "questioned", "withdrawn"]
Disposition = Literal["kill", "pivot", "candidate"]

VALID_CLAIM_STATUSES = {"supported", "unsupported", "unresolved", "withdrawn"}
VALID_SOURCE_STANDINGS = {"active", "questioned", "withdrawn"}
VALID_DISPOSITIONS = {"kill", "pivot", "candidate"}

@dataclass
class SourceRef:
    source_id: str
    title: str
    locator: str
    primary: bool = True
    standing: SourceStanding = "active"
    notes: str = ""

@dataclass
class Claim:
    claim_id: str
    text: str
    status: ClaimStatus
    source_ids: List[str] = field(default_factory=list)
    uncertainty: str = ""
    depends_on: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)

@dataclass
class Objection:
    objection_id: str
    target: str
    text: str
    basis: str
    resolved: bool = False
    resolution: str = ""

@dataclass
class Investigation:
    investigation_id: str
    title: str
    question: str
    initial_hypothesis: str
    sources: List[SourceRef] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    objections: List[Objection] = field(default_factory=list)
    discovery_delta: str = ""
    result_summary: str = ""
    disposition: Optional[Disposition] = None
    disposition_reason: str = ""
    reopened_from_hash: str = ""

    def to_dict(self):
        return asdict(self)
