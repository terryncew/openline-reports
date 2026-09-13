"""Swarm-facing proposal contract; the swarm has no identity-admission authority."""
from __future__ import annotations
from typing import Any
_ALLOWED={"attribute","target_value","candidate_value","source_id","provenance_status","authoritative"}
def make_identity_binding_proposal(*,proposal_id:str,target_entity:str,candidate_entity:str,evidence:list[dict[str,Any]])->dict[str,Any]:
    if not proposal_id or not target_entity or not candidate_entity: raise ValueError("identity_binding_required_field")
    normalized=[]
    for item in evidence:
        extra=set(item)-_ALLOWED
        if extra: raise ValueError("identity_binding_unknown_evidence_field:"+",".join(sorted(extra)))
        for required in ("attribute","target_value","candidate_value","source_id"):
            if required not in item: raise ValueError("identity_binding_missing_evidence_field:"+required)
        row=dict(item); row.setdefault("provenance_status","VERIFIED"); row.setdefault("authoritative",False); normalized.append(row)
    return {"schema":"openline.identity-binding.proposal.v1","proposal_id":proposal_id,"target_entity":target_entity,"candidate_entity":candidate_entity,"evidence":normalized,"requested_disposition":None,"authority":"NONE"}
