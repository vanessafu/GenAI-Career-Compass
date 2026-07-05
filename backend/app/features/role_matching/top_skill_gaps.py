"""
Build user-facing Top Skill Gaps from raw gap_analysis SkillGap records.

This module only ranks existing gaps and writes actionable copy; upstream
matching remains the source of truth. Ranking uses role importance, missingness,
domain deficit, evidence gap, proof signal, and skill specificity, with a small
penalty for broad/generic skills. Career-path LLM output may polish wording but
must not choose, add, remove, or reorder gaps.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.role_matching.normalization import normalize_skill_key
from backend.app.features.role_matching.schemas import ActionableSkillGap, GapReport, SkillGap

logger = logging.getLogger("CareerCompass.RoleMatching.TopSkillGaps")


MAX_TOP_ACTIONABLE_GAPS = 3
GENERIC_SPECIFICITY_PENALTY_SCALE = 0.16

PRIORITY_SCORE_WEIGHTS = {
    "importance": 0.35,      # Prioritize skills marked essential/important for the target role.
    "missingness": 0.25,     # Prioritize skills where the user has little or no transferable signal.
    "domain_deficit": 0.10,  # Prioritize gaps in weak Skill Map domains, not isolated weak skills only.
    "evidence_gap": 0.10,    # Prioritize gaps with no direct profile evidence over partial/indirect evidence.
    "proof_signal": 0.05,    # Slightly favor gaps that can become clear resume/interview proof.
    "specificity": 0.15,     # Prefer concrete, role-actionable skills over broad soft/generic traits.
}

IMPORTANCE_SCORE = {"essential": 1.0, "important": 0.65, "nice_to_have": 0.3, "": 0.5}
SOURCE_EVIDENCE_GAP = {
    "": 1.0,
    "shared_alignment": 1.0,
    "context": 0.6,
    "ontology_implied": 0.45,
    "reverse_partial": 0.5,
}
PROOF_SIGNAL = {
    "softskills": 0.65,
    "soft skills": 0.65,
    "security": 0.95,
    "networking": 0.95,
    "software engineering": 0.9,
    "cloud": 0.95,
    "devops": 0.95,
    "databases": 0.9,
    "backend": 0.9,
    "frontend": 0.9,
    "data engineering": 0.9,
    "ai": 0.85,
}

# Small seed list for obviously broad traits. This is intentionally not a full
# whitelist/blacklist system; most specificity comes from domain and text
# heuristics below so role data can evolve without constant hand tuning.
GENERIC_SKILL_EXACT = {
    "adaptability",
    "analytical skills",
    "attention to detail",
    "collaboration",
    "communication",
    "critical thinking",
    "leadership",
    "problem solving",
    "teamwork",
    "time management",
}

GENERIC_SKILL_PHRASES = {
    "communication",
    "collaboration",
    "leadership",
    "problem solving",
    "teamwork",
}

SOFT_SKILL_DOMAIN_KEYS = {"softskills", "soft skills", "interpersonal skills"}

TECHNICAL_SPECIFICITY_MARKERS = {
    "api",
    "aws",
    "azure",
    "ci cd",
    "css",
    "dns",
    "docker",
    "ethereum",
    "gcp",
    "git",
    "html",
    "javascript",
    "kubernetes",
    "linux",
    "node",
    "python",
    "react",
    "rest",
    "sql",
    "terraform",
    "typescript",
    "web3",
}

DOMAIN_ACTIONS = {
    "security": (
        "Create a small security-support case study for {skill}: document the risk, the user-impacting symptom, "
        "the check you performed, and the prevention step you would recommend."
    ),
    "networking": (
        "Build a networking troubleshooting note for {skill}: reproduce a connectivity issue, inspect IP/DNS/TCP "
        "signals, and write the resolution as a support ticket."
    ),
    "software engineering": (
        "Turn {skill} into hands-on support evidence: complete a small lab task, capture the steps, and document "
        "the failure mode you diagnosed."
    ),
    "softskills": (
        "Show {skill} through one concrete support scenario: describe the user need, your response, and how you "
        "kept the interaction clear and actionable."
    ),
    "soft skills": (
        "Show {skill} through one concrete support scenario: describe the user need, your response, and how you "
        "kept the interaction clear and actionable."
    ),
    "cloud": (
        "Build a small cloud lab around {skill}: deploy or configure one service, capture the setup choices, and "
        "document what you would monitor or troubleshoot."
    ),
    "devops": (
        "Create a reproducible {skill} workflow: automate one setup or deployment step and document the commands, "
        "failure points, and rollback path."
    ),
    "databases": (
        "Practice {skill} with a small dataset: model one table/query workflow, test a failure case, and document "
        "how you validated the result."
    ),
    "backend": (
        "Build a compact backend task for {skill}: implement one endpoint or integration and document inputs, "
        "outputs, errors, and tests."
    ),
    "frontend": (
        "Build a small UI proof for {skill}: implement one interactive component and document accessibility, "
        "state handling, and edge cases."
    ),
    "data engineering": (
        "Create a mini pipeline for {skill}: ingest sample data, transform it, validate the output, and document "
        "how failures are detected."
    ),
    "ai": (
        "Create a compact experiment for {skill}: define the task, run a baseline, record the result, and explain "
        "what you would improve next."
    ),
}


@dataclass(frozen=True)
class GapPriority:
    score: float
    domain_deficit: float
    evidence_gap: float
    proof_signal: float
    specificity: float
    generic_penalty: float


@dataclass(frozen=True)
class RankedActionableGap:
    item: ActionableSkillGap
    priority_score: float
    importance_rank: int
    transferability: float


def enrich_gap_report_with_recommendations(
    report: GapReport,
    confirmed_profile: ConfirmedCVData,
    *,
    limit: int = MAX_TOP_ACTIONABLE_GAPS,
) -> GapReport:
    """Attach deterministic, user-specific recommendations to a gap report.

    Skill matching remains the source of truth. This layer only ranks already
    computed gaps and converts them into recruiter-facing actions and proof
    suggestions.
    """
    logger.debug(
        "Ranking top skill gaps: role_id=%s job_title=%r raw_gap_count=%d limit=%d",
        report.role_id,
        report.job_title,
        len(report.skills.skill_gaps),
        limit,
    )
    ranked = [_ranked_actionable_gap(report, gap) for gap in report.skills.skill_gaps if _gap_label(gap)]
    ranked.sort(
        key=lambda item: (
            -item.priority_score,
            item.importance_rank,
            item.transferability,
            item.item.display.casefold(),
        )
    )
    report.top_actionable_skill_gaps = [item.item for item in ranked[: max(0, limit)]]

    suggestions = {item.item.skill: item.item.suggested_action for item in ranked}
    for gap in report.skills.skill_gaps:
        gap.suggestion = suggestions.get(gap.required_skill) or _fallback_suggestion(gap)

    logger.info(
        "Top skill gaps selected: role_id=%s selected=%s",
        report.role_id,
        [
            {
                "skill": item.item.skill,
                "domain": item.item.domain,
                "priority_label": item.item.priority_label,
                "priority_score": round(item.priority_score, 4),
            }
            for item in ranked[: max(0, limit)]
        ],
    )
    return report


def _ranked_actionable_gap(report: GapReport, gap: SkillGap) -> RankedActionableGap:
    label = _gap_label(gap)
    domain = _gap_domain(report, gap)
    priority = _priority(report, gap, domain)
    closest = gap.user_closest_skill
    signal_status = _signal_status(gap)
    action = _suggested_action(label, domain, closest, signal_status)

    return RankedActionableGap(
        item=ActionableSkillGap(
            skill=gap.required_skill,
            display=label,
            domain=domain,
            priority_label=_priority_label(priority.score),
            estimated_effort=_estimated_effort(gap),
            bridge_skill=closest,
            why_it_matters=_why_it_matters(report, label, domain, gap.importance),
            suggested_action=action,
            proof_to_build=_proof_to_build(label, domain),
            resume_hint=_resume_hint(label, domain, closest),
        ),
        priority_score=priority.score,
        importance_rank=_importance_rank(gap.importance),
        transferability=gap.transferability,
    )


def _priority(report: GapReport, gap: SkillGap, domain: str) -> GapPriority:
    importance = IMPORTANCE_SCORE.get(gap.importance, IMPORTANCE_SCORE[""])
    missingness = 1.0 - _clamp01(gap.transferability)
    domain_coverage = _domain_coverage(report, domain)
    domain_deficit = 1.0 - domain_coverage
    evidence_gap = SOURCE_EVIDENCE_GAP.get(gap.source, 0.75)
    proof_signal = PROOF_SIGNAL.get(_domain_key(domain), 0.75)
    specificity = _specificity_signal(_gap_label(gap), domain)
    generic_penalty = GENERIC_SPECIFICITY_PENALTY_SCALE * (1.0 - specificity)
    score = (
        PRIORITY_SCORE_WEIGHTS["importance"] * importance
        + PRIORITY_SCORE_WEIGHTS["missingness"] * missingness
        + PRIORITY_SCORE_WEIGHTS["domain_deficit"] * domain_deficit
        + PRIORITY_SCORE_WEIGHTS["evidence_gap"] * evidence_gap
        + PRIORITY_SCORE_WEIGHTS["proof_signal"] * proof_signal
        + PRIORITY_SCORE_WEIGHTS["specificity"] * specificity
        - generic_penalty
    )
    return GapPriority(
        score=_clamp01(score),
        domain_deficit=domain_deficit,
        evidence_gap=evidence_gap,
        proof_signal=proof_signal,
        specificity=specificity,
        generic_penalty=generic_penalty,
    )


def _gap_domain(report: GapReport, gap: SkillGap) -> str:
    if _clean(gap.domain):
        return _clean(gap.domain)
    label = _gap_label(gap)
    for domain, skills in report.skills.domain_skills.items():
        if any(normalize_skill_key(skill) == normalize_skill_key(label) for skill in skills):
            return domain
    return label


def _domain_coverage(report: GapReport, domain: str) -> float:
    if domain in report.skills.domain_coverage:
        return _clamp01(report.skills.domain_coverage[domain])
    domain_key = _domain_key(domain)
    for known_domain, value in report.skills.domain_coverage.items():
        if _domain_key(known_domain) == domain_key:
            return _clamp01(value)
    return 0.0


def _why_it_matters(report: GapReport, label: str, domain: str, importance: str) -> str:
    role = _clean(report.job_title) or "this target role"
    importance_text = {
        "essential": "a core requirement",
        "important": "an important signal",
        "nice_to_have": "a useful differentiator",
    }.get(importance, "a visible requirement")
    if domain and domain != label:
        return f"{label} is {importance_text} for {role} and sits in the {domain} area recruiters will scan for."
    return f"{label} is {importance_text} for {role}, so it needs visible evidence in the profile."


def _suggested_action(
    label: str,
    domain: str,
    closest: str | None,
    signal_status: str,
) -> str:
    base = DOMAIN_ACTIONS.get(_domain_key(domain)) or (
        "Create one concrete proof point for {skill}: complete a small task, document the context, "
        "and capture the result in a way a recruiter can verify."
    )
    action = base.format(skill=label)
    if closest and signal_status != "missing":
        return f"Use your existing {closest} signal as the bridge. {action}"
    return action


def _proof_to_build(label: str, domain: str) -> str:
    domain_key = _domain_key(domain)
    if domain_key in {"softskills", "soft skills"}:
        return f"A short STAR-style example showing how you used {label} with a user, teammate, or stakeholder."
    if domain_key in {"security", "networking", "software engineering", "cloud", "devops"}:
        return f"A support-style lab note or project README that shows the {label} task, diagnosis steps, and outcome."
    return f"A compact project note or portfolio entry that shows where {label} was used and what changed because of it."


def _resume_hint(label: str, domain: str, closest: str | None) -> str:
    bridge = f" building on {closest}" if closest else ""
    if _domain_key(domain) in {"softskills", "soft skills"}:
        return f"Add one bullet that proves {label}{bridge} through a specific situation, action, and result."
    return f"Add one bullet that names {label}{bridge}, the tool or environment, the problem solved, and a measurable or observable result."


def _estimated_effort(gap: SkillGap) -> str:
    if gap.transferability >= 0.75:
        return "quick_win"
    if gap.transferability > 0:
        return "moderate"
    return "substantial"


def _signal_status(gap: SkillGap) -> str:
    if gap.transferability <= 0:
        return "missing"
    if gap.source == "context":
        return "weakly_evidenced"
    return "partial"


def _specificity_signal(label: str, domain: str) -> float:
    """Score whether a gap is concrete enough to be a useful top recommendation."""
    key = normalize_skill_key(label)
    domain_key = _domain_key(domain)

    if _has_technical_marker(key):
        return 0.95
    if key in GENERIC_SKILL_EXACT:
        return 0.20
    if domain_key in SOFT_SKILL_DOMAIN_KEYS:
        return 0.35
    if any(phrase in key for phrase in GENERIC_SKILL_PHRASES):
        return 0.45
    if len(key.split()) >= 2:
        return 0.85
    return 0.70


def _has_technical_marker(skill_key: str) -> bool:
    tokens = set(skill_key.split())
    return any(
        marker == skill_key or marker in tokens or marker in skill_key
        for marker in TECHNICAL_SPECIFICITY_MARKERS
    )


def _priority_label(score: float) -> str:
    if score >= 0.82:
        return "critical"
    if score >= 0.68:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _fallback_suggestion(gap: SkillGap) -> str:
    label = _gap_label(gap)
    if gap.user_closest_skill and gap.transferability > 0:
        return f"Use your existing {gap.user_closest_skill} evidence as a bridge and add a concrete proof point for {label}."
    return f"Add a concrete project, lab note, or resume bullet that makes {label} visible."


def _gap_label(gap: SkillGap) -> str:
    return _clean(gap.display) or _clean(gap.required_skill) or _clean(gap.skill)


def _importance_rank(value: str) -> int:
    return {"essential": 0, "important": 1, "nice_to_have": 2}.get(value, 3)


def _domain_key(domain: str) -> str:
    return normalize_skill_key(domain).replace(" ", " ")


def _clean(value: str | None) -> str:
    return " ".join(str(value or "").split())


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
