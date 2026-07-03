"""Shared skill-key, certification, and seniority normalization.

Both role matching (service.py) and gap analysis (gap_analysis.py) compare a
user against the same role catalog and must agree on what counts as "the same
skill", "the same certification", and "the same seniority level" - otherwise
the two pages can reach different conclusions for the same user/role pair.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Skill keys
# ---------------------------------------------------------------------------


def normalize_skill_key(value: str | None) -> str:
    value = (value or "").casefold()
    value = re.sub(r"[^a-z0-9+#]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_alias_map(alias_map: dict[str, str]) -> dict[str, str]:
    return {
        normalize_skill_key(alias): normalize_skill_key(canonical)
        for alias, canonical in alias_map.items()
        if normalize_skill_key(alias) and normalize_skill_key(canonical)
    }


# ---------------------------------------------------------------------------
# career_roles.sort_skills - [{"skill", "domain", "score"}], LLM-enhanced and
# reranked by backend/scripts/role_embeddings.py. This is the primary source
# of truth for a role's required skills; role_skills/raw_skills are only a
# fallback for roles never reprocessed with it.
# ---------------------------------------------------------------------------


def required_skills_from_sort_skills(sort_skills: list[dict] | None) -> list[str]:
    """sort_skills -> ordered, deduped required-skill list."""
    names: list[str] = []
    seen: set[str] = set()
    for item in sort_skills or []:
        if not isinstance(item, dict):
            continue
        key = normalize_skill_key(item.get("skill"))
        if key and key not in seen:
            seen.add(key)
            names.append(key)
    return names


def skill_weight_map(sort_skills: list[dict] | None) -> dict[str, float]:
    """sort_skills -> {normalized_skill: 0-1 importance score}."""
    weights: dict[str, float] = {}
    for item in sort_skills or []:
        if not isinstance(item, dict):
            continue
        key = normalize_skill_key(item.get("skill"))
        score = item.get("score")
        if key and isinstance(score, (int, float)):
            weights[key] = float(score)
    return weights


def skill_domain_map(sort_skills: list[dict] | None) -> dict[str, str]:
    """sort_skills -> {normalized_skill: domain label}."""
    domains: dict[str, str] = {}
    for item in sort_skills or []:
        if not isinstance(item, dict):
            continue
        key = normalize_skill_key(item.get("skill"))
        domain = item.get("domain")
        if key and isinstance(domain, str) and domain.strip():
            domains[key] = domain.strip()
    return domains


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


def normalize_certification_name(name: str | None) -> str:
    value = (name or "").casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


CERTIFICATION_ALIAS_GROUPS_RAW: tuple[tuple[str, ...], ...] = (
    (
        "Google Data Analytics Certificate",
        "Google Data Analytics Professional Certificate",
    ),
    (
        "Oracle Certified Associate Java Programmer",
        "Oracle Certified Associate (OCA) - Java",
        "Oracle Java Programmer Certification",
        "OCA Java",
    ),
    (
        "CompTIA A+",
        "CompTIA A Plus",
        "CompTIA A+ Certification",
    ),
)

_CERTIFICATION_ALIAS_GROUPS = tuple(
    frozenset(
        normalized
        for normalized in (normalize_certification_name(name) for name in group)
        if normalized
    )
    for group in CERTIFICATION_ALIAS_GROUPS_RAW
)
_CERTIFICATION_ALIAS_MAP = {alias: group for group in _CERTIFICATION_ALIAS_GROUPS for alias in group}


def certification_match_keys(name: str | None) -> set[str]:
    normalized = normalize_certification_name(name)
    if not normalized:
        return set()
    return set(_CERTIFICATION_ALIAS_MAP.get(normalized, {normalized}))


def normalize_user_certifications(certification_names: Iterable[str | None]) -> set[str]:
    normalized: set[str] = set()
    for name in certification_names:
        normalized.update(certification_match_keys(name))
    return normalized


# ---------------------------------------------------------------------------
# Seniority
# ---------------------------------------------------------------------------

SENIORITY_ORDER = ["intern", "junior", "mid", "senior", "lead", "staff", "principal", "director"]
SENIORITY_ALIASES = {
    "entry": "junior",
    "entry level": "junior",
    "associate": "junior",
    "apprentice": "junior",
    "beginner": "junior",
    "graduate": "junior",
    "jr": "junior",
    "student": "junior",
    "trainee": "junior",
    "intermediate": "mid",
    "regular": "mid",
    "sr": "senior",
    "snr": "senior",
    "architect": "lead",
    "team lead": "lead",
    "tech lead": "lead",
    "head": "director",
    "vp": "director",
    "chief": "director",
}


def seniority_level_from_title(title: str | None) -> Optional[str]:
    """Extract a canonical seniority level from a free-text role/job title."""
    text = " " + normalize_skill_key(title) + " "
    for level in reversed(SENIORITY_ORDER):
        if f" {level} " in text:
            return level
    for alias, level in SENIORITY_ALIASES.items():
        if f" {alias} " in text:
            return level
    return None


def canon_seniority_label(label: Optional[str]) -> Optional[str]:
    """Canonicalize an already-structured seniority label (e.g. a CV's
    current_seniority_level field), as opposed to a free-text title."""
    if not label:
        return None
    key = label.strip().casefold()
    key = SENIORITY_ALIASES.get(key, key)
    return key if key in SENIORITY_ORDER else None


def seniority_gap(user_level: Optional[str], role_level: Optional[str]) -> tuple[str, float]:
    """Compare two canonical seniority levels. Returns (gap_label, fit_score)."""
    if not user_level or not role_level:
        return "unknown", 0.70

    distance = SENIORITY_ORDER.index(role_level) - SENIORITY_ORDER.index(user_level)
    if distance == 0:
        return "match", 1.0
    if distance > 0:
        return "stretch", max(0.25, 0.65 - (0.20 * (distance - 1)))
    return "overqualified", max(0.75, 0.90 - (0.05 * (abs(distance) - 1)))
