"""Precomputed, role-agnostic user-skill preparation.

Used internally to normalize a profile and walk the MIND ontology once per
role-matching request rather than once per catalog role.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.features.role_matching.normalization import canon_skill, dedupe_clean
from backend.app.features.role_matching.skill_ontology import (
    canonical_skill_key,
    get_ontology,
    hop_confidence,
)

CURRENT_PREPARED_SKILLS_VERSION = 1


@dataclass(frozen=True)
class SkillEvidence:
    explicit_terms: list[str] = field(default_factory=list)
    context_terms: list[str] = field(default_factory=list)


class PreparedSkillEntry(BaseModel):
    key: str
    display: str
    source: Literal["explicit", "context", "ontology_implied"]
    confidence: float = 1.0
    # explicit/context: always 1.0 - a presence flag ("this term is in the user's
    #   profile at this evidence tier"), not a match credit. The real match credit
    #   (FULL/TOKEN/CONTEXT) is decided per-required-skill inside align_skills, same
    #   as today.
    # ontology_implied: confidence IS the final match credit (hop_confidence(hop)).
    via: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)


class PreparedSkillProfile(BaseModel):
    version: int = CURRENT_PREPARED_SKILLS_VERSION
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    entries: list[PreparedSkillEntry] = Field(default_factory=list)


def prepare_user_skills(
    evidence: SkillEvidence, alias_map: dict[str, str] | None = None
) -> PreparedSkillProfile:
    """normalize_skill_key -> alias_map -> ontology.canonical() -> hop-decayed
    closure. Role-agnostic; safe to compute once and reuse across every role."""
    aliases = alias_map or {}
    ontology = get_ontology()

    entries: list[PreparedSkillEntry] = []
    seen_keys: set[str] = set()

    explicit_clean = dedupe_clean(evidence.explicit_terms)
    for term in explicit_clean:
        key = canonical_skill_key(term, aliases)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(PreparedSkillEntry(key=key, display=term, source="explicit"))

    context_clean = dedupe_clean(evidence.context_terms)
    for term in context_clean:
        key = canonical_skill_key(term, aliases)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(PreparedSkillEntry(key=key, display=term, source="context"))

    implied = ontology.implied_with_hops(explicit_clean)
    for mind_name, hit in implied.items():
        key = canon_skill(mind_name, aliases)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(
            PreparedSkillEntry(
                key=key,
                display=mind_name,
                source="ontology_implied",
                confidence=hop_confidence(hit.hop),
                via=[hit.via],
                domains=ontology.domain_hint(mind_name),
            )
        )

    return PreparedSkillProfile(entries=entries)
