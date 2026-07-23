from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, TypeVar

_T = TypeVar("_T")

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.role_matching.normalization import (
    canon_skill as _canon,
    clean_alias_map,
    compact_skill_key as _compact,
    dedupe_clean as _dedupe,
    normalize_skill_key,
)
from backend.app.features.role_matching.prepared_skills import (
    PreparedSkillProfile,
    SkillEvidence,
)
from backend.app.features.role_matching.skill_ontology import (
    canonical_skill_key,
    get_ontology,
    hop_confidence,
)

FULL_CREDIT = 1.0
TOKEN_CREDIT = 0.75
CONTEXT_CREDIT = 0.6
REVERSE_PARTIAL_CREDIT = 0.40  # role wants X, user only holds a prerequisite of X

# Skill importance weighting (0-1 scores from career_roles.sort_skills).
# Tiers mirror the Gemini ranking prompt in backend/scripts/role_embeddings.py.
ESSENTIAL_WEIGHT = 0.75
IMPORTANT_WEIGHT = 0.40
DEFAULT_SKILL_WEIGHT = 0.5  # used when a required skill has no known importance score
_IMPORTANCE_RANK = {"essential": 0, "important": 1, "nice_to_have": 2, "": 3}


def skill_importance_tier(weight: float | None) -> str:
    if weight is None:
        return ""
    if weight >= ESSENTIAL_WEIGHT:
        return "essential"
    if weight >= IMPORTANT_WEIGHT:
        return "important"
    return "nice_to_have"


@dataclass(frozen=True)
class SkillAlignment:
    coverage: float
    matched_skills: list[str]
    missing_skills: list[str]
    skill_gaps: list[dict[str, Any]]
    domain_scores: dict[str, float] = field(default_factory=dict)
    domain_skills: dict[str, list[str]] = field(default_factory=dict)


def _text_parts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _cv_data(profile: ConfirmedCVData | CVData) -> CVData:
    return profile.confirmed_cv_data if isinstance(profile, ConfirmedCVData) else profile


def build_skill_evidence_from_confirmed_profile(profile: ConfirmedCVData | CVData) -> SkillEvidence:
    cv = _cv_data(profile)
    explicit: list[str] = []
    context: list[str] = []

    context.extend(
        [
            cv.personal_info.current_role,
            cv.profile_summary.summary,
            cv.profile_summary.current_seniority_level,
            *cv.interests,
        ]
    )

    for skill in cv.skills_extracted.technical_skills:
        explicit.append(skill.name)
    for inferred in cv.skills_extracted.inferred_skills:
        explicit.append(inferred.name)
    for soft_skill in cv.skills_extracted.soft_skills:
        explicit.append(soft_skill.name)

    for exp in cv.experience:
        context.extend([exp.role, exp.industry, *exp.core_responsibilities])
        explicit.extend(exp.contextual_skills)

    for education in cv.education:
        context.extend(
            [
                education.degree_type,
                education.field_of_study,
                education.institution,
                education.thesis_title,
                *education.courses,
            ]
        )

    for project in cv.projects:
        context.extend([project.title, project.description, project.role, *project.outcomes])
        explicit.extend(project.technologies)

    for thesis in cv.thesis:
        context.extend([thesis.title, thesis.degree_type, thesis.institution, thesis.description])
        explicit.extend(thesis.technologies)

    return SkillEvidence(explicit_terms=_dedupe(explicit), context_terms=_dedupe(context))


def build_skill_evidence_from_user_profile(profile: Any) -> SkillEvidence:
    explicit: list[str] = []
    context: list[str] = []

    identity = getattr(profile, "career_identity", None)
    context.extend([getattr(identity, "title", None), getattr(identity, "summary", None)])
    context.extend(_text_parts(getattr(profile, "interests", None)))
    explicit.extend(_text_parts(getattr(profile, "skills", None)))

    for exp in getattr(profile, "experience", None) or []:
        context.extend([getattr(exp, "role", None), getattr(exp, "summary", None)])
        explicit.extend(_text_parts(getattr(exp, "skills", None)))

    for education in getattr(profile, "education", None) or []:
        context.extend([getattr(education, "degree", None), getattr(education, "institution", None)])

    for project in getattr(profile, "projects", None) or []:
        context.extend([getattr(project, "title", None), getattr(project, "summary", None)])
        explicit.extend(_text_parts(getattr(project, "technologies", None)))

    for certification in getattr(profile, "certifications", None) or []:
        context.extend([getattr(certification, "name", None), getattr(certification, "issuer", None)])

    return SkillEvidence(explicit_terms=_dedupe(explicit), context_terms=_dedupe(context))


def _variant_match(required: str, candidate: str) -> bool:
    if required == candidate:
        return True

    required_compact = _compact(required)
    candidate_compact = _compact(candidate)
    if required_compact and required_compact == candidate_compact:
        return True

    if required_compact and re.fullmatch(re.escape(required_compact) + r"\d+", candidate_compact):
        return True
    if candidate_compact and re.fullmatch(re.escape(candidate_compact) + r"\d+", required_compact):
        return True

    return False


def _token_score(required: str, candidate: str) -> float:
    req_tokens = {_singular_token(token) for token in required.split()}
    cand_tokens = {_singular_token(token) for token in candidate.split()}
    if not req_tokens or not cand_tokens:
        return 0.0
    if req_tokens <= cand_tokens or cand_tokens <= req_tokens:
        return TOKEN_CREDIT
    overlap = req_tokens & cand_tokens
    if overlap and len(overlap) / len(req_tokens) >= 0.5:
        return TOKEN_CREDIT
    return 0.0


def _singular_token(token: str) -> str:
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _best_score(required: str, candidates: Iterable[str], alias_map: dict[str, str]) -> tuple[float, str | None]:
    best_score = 0.0
    best_candidate: str | None = None
    for candidate in candidates:
        canonical = _canon(candidate, alias_map)
        if _variant_match(required, canonical):
            return FULL_CREDIT, canonical
        score = _token_score(required, canonical)
        if score > best_score:
            best_score = score
            best_candidate = canonical
    return best_score, best_candidate


def _context_score(required: str, context_terms: Iterable[str], alias_map: dict[str, str]) -> tuple[float, str | None]:
    required_compact = _compact(required)
    for term in context_terms:
        normalized = _canon(term, alias_map)
        if _variant_match(required, normalized) or _token_score(required, normalized) > 0:
            return CONTEXT_CREDIT, normalized
        text = " " + normalize_skill_key(term) + " "
        if f" {required} " in text or (required_compact and required_compact in _compact(term)):
            return CONTEXT_CREDIT, normalize_skill_key(term)
    return 0.0, None


def _severity(score: float) -> str:
    if score >= FULL_CREDIT:
        return "matched"
    if score >= TOKEN_CREDIT:
        return "low"
    if score > 0:
        return "medium"
    return "high"


def _implied_lookup_from_prepared(prepared: PreparedSkillProfile) -> dict[str, tuple[float, str]]:
    return {
        entry.key: (entry.confidence, ", ".join(entry.via) or entry.display)
        for entry in prepared.entries
        if entry.source == "ontology_implied"
    }


def _implied_lookup_from_evidence(
    explicit_terms: Iterable[str], aliases: dict[str, str]
) -> dict[str, tuple[float, str]]:
    expanded = get_ontology().implied_with_hops(explicit_terms)
    return {
        _canon(mind_name, aliases): (hop_confidence(hit.hop), hit.via)
        for mind_name, hit in expanded.items()
    }


def _ontology_domain_hint(key: str) -> str | None:
    """Bridge our normalized key-space into the ontology's own canonical
    names (MIND stores nodes like "Next.js", not "next js"), then read its
    technicalDomains/associatedToApplicationDomains hint."""
    mind_name = get_ontology().canonical(key)
    if not mind_name:
        return None
    hints = get_ontology().domain_hint(mind_name)
    return hints[0] if hints else None


def _reverse_prereq_match(required_skill: str, held_canonical: set[str], aliases: dict[str, str]) -> str | None:
    """Does the user hold a PREREQUISITE of required_skill (role wants Next.js,
    user only has React)? Depends on the specific required skill, so this can't
    be precomputed at user-prep time - it's a cheap runtime lookup instead,
    memoized process-wide via SkillOntology._closure_cache."""
    ontology = get_ontology()
    mind_name = ontology.canonical(required_skill)
    if not mind_name:
        return None
    prereqs = {_canon(name, aliases) for name in ontology.implied_closure(mind_name)} - {required_skill}
    hit = held_canonical & prereqs
    return next(iter(hit)) if hit else None


def _canon_value_map(
    items: dict[str, _T], aliases: dict[str, str], *, use_ontology: bool = False
) -> dict[str, _T]:
    """Canon-map a {raw_skill_key: value} dict to {canonical_key: value},
    preferring the entry whose own key IS the canonical form when multiple
    raw keys alias into the same canonical bucket (e.g. sort_skills lists both
    "UI/UX Design" and "Figma", and skill_aliases treats "figma" as an alias of
    "ui ux design" for matching - without this, plain dict-comprehension
    last-write-wins would pick whichever happened to be inserted last,
    silently discarding UI/UX Design's own weight/domain/display in favor of
    Figma's)."""
    result: dict[str, _T] = {}
    for raw_key, value in items.items():
        own_key = normalize_skill_key(raw_key)
        canon_key = (
            canonical_skill_key(raw_key, aliases)
            if use_ontology
            else aliases.get(own_key, own_key)
        )
        if canon_key == own_key or canon_key not in result:
            result[canon_key] = value
    return result


def align_skills(
    required_skills: Iterable[str],
    evidence: SkillEvidence | None = None,
    alias_map: dict[str, str] | None = None,
    skill_weights: dict[str, float] | None = None,
    skill_domains: dict[str, str] | None = None,
    prepared: PreparedSkillProfile | None = None,
    enable_ontology_tiers: bool = False,
    skill_display: dict[str, str] | None = None,
) -> SkillAlignment:
    """skill_weights maps canonical skill keys to a 0-1 importance score, and
    skill_domains maps them to an industry-category label (e.g. "Backend") -
    both sourced from career_roles.sort_skills. When skill_weights is given,
    coverage is importance-weighted and each skill_gap gets an `importance`
    tier instead of every skill counting equally; skill_domains (if given)
    attaches a `domain` to each gap for domain-level grouping downstream.
    skill_display (also sourced from sort_skills, see normalization.py's
    skill_display_map) maps canonical keys to their original, properly-cased
    text - purely for display (gap/domain-fallback labels), never for
    matching; omitting it leaves every display value equal to the normalized
    key exactly as before, so existing callers (e.g. /match's service.py,
    which never passes it) are unaffected.

    Pass exactly one of `evidence` (raw CV text, re-normalized and re-run
    through the ontology closure on every call) or `prepared` (precomputed
    once via prepare_user_skills(), see prepared_skills.py). `prepared` takes
    precedence if both are given, and always engages the ontology-aware score
    tiers below; for the `evidence` path they're opt-in via
    `enable_ontology_tiers` so existing callers (the /match recommendation
    flow) keep their exact current scoring unless they ask for the new tiers."""
    aliases = clean_alias_map(alias_map or {})
    use_ontology_tiers = enable_ontology_tiers or prepared is not None

    def alignment_key(skill: str) -> str:
        if use_ontology_tiers:
            return canonical_skill_key(skill, aliases)
        return _canon(skill, aliases)

    required = _dedupe(alignment_key(skill) for skill in required_skills)
    if not required:
        return SkillAlignment(coverage=0.0, matched_skills=[], missing_skills=[], skill_gaps=[])

    weights = _canon_value_map(skill_weights or {}, aliases, use_ontology=use_ontology_tiers)
    domains = _canon_value_map(skill_domains or {}, aliases, use_ontology=use_ontology_tiers)
    display_map = _canon_value_map(skill_display or {}, aliases, use_ontology=use_ontology_tiers)

    if prepared is not None:
        explicit = [entry.key for entry in prepared.entries if entry.source == "explicit"]
        context_pool: list[str] = [entry.key for entry in prepared.entries if entry.source == "context"]
        implied_lookup = _implied_lookup_from_prepared(prepared)
        held_canonical = {
            entry.key for entry in prepared.entries if entry.source in ("explicit", "ontology_implied")
        }
        user_display = {entry.key: entry.display for entry in prepared.entries}
    else:
        evidence = evidence or SkillEvidence()
        explicit = _dedupe(alignment_key(skill) for skill in evidence.explicit_terms)
        context_pool = [alignment_key(term) for term in evidence.context_terms]
        if use_ontology_tiers:
            implied_lookup = _implied_lookup_from_evidence(evidence.explicit_terms, aliases)
            held_canonical = set(explicit) | set(implied_lookup)
        else:
            implied_lookup = {}
            held_canonical = set()
        user_display = {}
        for term in (*evidence.explicit_terms, *evidence.context_terms):
            user_display.setdefault(alignment_key(term), term)

    matched: list[str] = []
    missing: list[str] = []
    gaps: list[dict[str, Any]] = []
    weighted_score_sum = 0.0
    weight_sum = 0.0
    domain_totals: dict[str, float] = {}
    domain_counts: dict[str, int] = {}
    domain_skills: dict[str, list[str]] = {}

    for required_skill in required:
        score, closest = _best_score(required_skill, explicit, aliases)
        source = "explicit" if score else ""

        if score == 0 and not use_ontology_tiers:
            score, closest = _context_score(required_skill, context_pool, aliases)
            source = "context" if score else ""
        elif score == 0 and use_ontology_tiers:
            hit = implied_lookup.get(required_skill)
            ontology_score = hit[0] if hit else 0.0
            context_score, context_closest = _context_score(required_skill, context_pool, aliases)
            reverse_closest = _reverse_prereq_match(required_skill, held_canonical, aliases)
            reverse_score = REVERSE_PARTIAL_CREDIT if reverse_closest else 0.0

            # These three fallback tiers straddle each other (hop-1 ontology
            # credit sits above CONTEXT_CREDIT, hop-2/3 sit below it), so take
            # the max rather than checking in a fixed order and stopping at
            # the first nonzero hit.
            best = max(ontology_score, context_score, reverse_score)
            if best > 0 and best == ontology_score:
                score, closest, source = ontology_score, hit[1], "ontology_implied"
            elif best > 0 and best == context_score:
                score, closest, source = context_score, context_closest, "context"
            elif best > 0 and best == reverse_score:
                score, closest, source = reverse_score, reverse_closest, "reverse_partial"

        weight = weights.get(required_skill, DEFAULT_SKILL_WEIGHT if weights else 1.0)
        weighted_score_sum += score * weight
        weight_sum += weight

        display_text = display_map.get(required_skill, required_skill)
        closest_display = user_display.get(closest, closest) if closest is not None else None

        # Domain fallback, three tiers: 1. LLM-curated tag (never overridden) ->
        # 2. the ontology's own primary technicalDomain, if the skill resolves ->
        # 3. the skill's own display text as a last-resort pseudo-domain.
        domain = domains.get(required_skill) or _ontology_domain_hint(required_skill) or display_text
        domain_totals[domain] = domain_totals.get(domain, 0.0) + score
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        domain_skills.setdefault(domain, []).append(display_text)

        if score >= TOKEN_CREDIT:
            matched.append(display_text)
        if score == 0:
            missing.append(display_text)
        if score < FULL_CREDIT:
            gaps.append(
                {
                    "required_skill": required_skill,
                    "display": display_text,
                    "user_closest_skill": closest_display,
                    "transferability": score,
                    "severity": _severity(score),
                    "importance": skill_importance_tier(weights.get(required_skill)),
                    "domain": domains.get(required_skill, ""),
                    "source": source,
                }
            )

    gaps.sort(key=lambda gap: (_IMPORTANCE_RANK.get(gap["importance"], 3), gap["transferability"]))

    domain_scores = {
        domain: round(total / domain_counts[domain], 4) for domain, total in domain_totals.items()
    }

    return SkillAlignment(
        coverage=weighted_score_sum / weight_sum if weight_sum else 0.0,
        matched_skills=matched,
        missing_skills=missing,
        skill_gaps=gaps,
        domain_scores=domain_scores,
        domain_skills=domain_skills,
    )
