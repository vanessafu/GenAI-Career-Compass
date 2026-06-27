from __future__ import annotations

import json
import logging
from typing import Iterable

from backend.app.core.openai_client import parse_structured
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.role_matching.gap_analysis import explain_role_gap
from backend.app.features.role_matching.schemas import (
    CareerPathDraft,
    CareerPathMilestone,
    CareerPathReport,
    CertificationGap,
    GapReport,
    SkillGap,
)

logger = logging.getLogger("CareerCompass.RoleMatching.CareerPath")

MAX_GAPS = 5
MAX_MILESTONES = 5

_SYSTEM_PROMPT = (
    "You generate concise career roadmap text from a precomputed gap report. "
    "Use only the supplied role requirements, readiness score, skill gaps, and "
    "certification gaps. Do not invent certifications, salaries, job markets, "
    "courses, bootcamps, or unsupported career claims. For every milestone, set "
    "kind to exactly one of: role, skill, project, certification, experience."
)


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def timeline_from_readiness(readiness: float | None) -> str:
    score = max(0.0, min(1.0, float(readiness or 0.0)))
    if score >= 0.75:
        return "1-3 months"
    if score >= 0.55:
        return "3-6 months"
    if score >= 0.35:
        return "6-9 months"
    return "9-12+ months"


def _unique(values: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _cert_name(gap: CertificationGap) -> str:
    return _clean(gap.required_certification or gap.name or gap.normalized_name)


def _allowed_certifications(report: GapReport) -> list[str]:
    return _unique(
        _cert_name(gap)
        for gap in [
            *report.certifications.missing,
            *report.certifications.missing_certifications,
            *report.certifications.related,
        ]
    )


def _filter_certifications(generated: list[str], allowed: list[str]) -> list[str]:
    by_key = {item.casefold(): item for item in allowed}
    return _unique(by_key.get(_clean(item).casefold()) for item in generated)


def _skill_name(gap: SkillGap) -> str:
    return _clean(gap.required_skill or gap.skill)


def _top_skill_gaps(report: GapReport) -> list[str]:
    rank = {"high": 0, "medium": 1, "low": 2}
    gaps = sorted(
        report.skills.skill_gaps,
        key=lambda gap: (rank.get(gap.severity, 3), gap.transferability),
    )
    return _unique(_skill_name(gap) for gap in gaps)[:MAX_GAPS]


def _profile_summary(profile: ConfirmedCVData) -> str:
    statement = _clean(profile.career_identity_statement)
    if statement:
        return statement

    cv = profile.confirmed_cv_data
    summary = _clean(cv.profile_summary.summary)
    role = _clean(cv.personal_info.current_role)
    if role and summary:
        return f"{role}: {summary}"
    return summary or role or "Current profile"


def _fallback_draft(gaps: list[str], allowed_certs: list[str]) -> CareerPathDraft:
    targets = gaps[:3]
    for generic in ("portfolio proof", "transition narrative", "target-role evidence"):
        if len(targets) >= 3:
            break
        targets.append(generic)

    milestones = [
        CareerPathMilestone(
            order=index + 1,
            kind=_fallback_kind(gap, allowed_certs),
            title=f"Build evidence for {gap}",
            timeline="2-4 weeks",
            rationale=f"This directly addresses the visible {gap} gap.",
            skills=[gap],
            projects=[f"Create a small project that demonstrates {gap}"],
        )
        for index, gap in enumerate(targets)
    ]

    return CareerPathDraft(
        milestones=milestones,
        recommended_projects=_unique(project for item in milestones for project in item.projects),
        estimated_timeline="2-3 months" if gaps else "1 month",
        certifications=allowed_certs,
    )


def _fallback_kind(target: str, allowed_certs: list[str]) -> str:
    key = target.casefold()
    cert_keys = {cert.casefold() for cert in allowed_certs}
    if key in cert_keys or "certif" in key or "exam" in key:
        return "certification"
    if "portfolio" in key or "project" in key or "proof" in key:
        return "project"
    if "role" in key:
        return "role"
    if "experience" in key or "transition" in key:
        return "experience"
    return "skill"


def _prompt_payload(
    report: GapReport,
    current_profile_summary: str,
    top_gaps: list[str],
    allowed_certs: list[str],
) -> dict:
    return {
        "current_profile_summary": current_profile_summary,
        "target_role": report.job_title,
        "readiness_score": round(report.overall_readiness or report.readiness_score, 3),
        "top_gaps": top_gaps,
        "matched_skills": report.skills.matched_skills[:10],
        "certification_gaps": allowed_certs,
        "allowed_milestone_kinds": ["role", "skill", "project", "certification", "experience"],
        "seniority": report.seniority.model_dump(mode="json"),
        "role_description": _clean(report.job_description)[:1200],
    }


async def _generate_draft(
    report: GapReport,
    current_profile_summary: str,
    top_gaps: list[str],
    allowed_certs: list[str],
) -> CareerPathDraft:
    try:
        draft = await parse_structured(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        _prompt_payload(report, current_profile_summary, top_gaps, allowed_certs),
                        ensure_ascii=False,
                    ),
                },
            ],
            response_format=CareerPathDraft,
            model_purpose="career_path",
        )
        if draft is not None:
            return draft
    except Exception as exc:
        logger.warning("Career path generation failed; using deterministic fallback: %s", exc)
    return _fallback_draft(top_gaps, allowed_certs)


def _normalize_milestones(milestones: list[CareerPathMilestone], gaps: list[str]) -> list[CareerPathMilestone]:
    selected = sorted(milestones, key=lambda item: item.order)[:MAX_MILESTONES]
    fallback = _fallback_draft(gaps, []).milestones
    seen = {_clean(item.title).casefold() for item in selected}

    for item in fallback:
        if len(selected) >= 3:
            break
        key = _clean(item.title).casefold()
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)

    return [
        CareerPathMilestone(
            order=index + 1,
            kind=item.kind,
            title=item.title,
            timeline=item.timeline,
            rationale=item.rationale,
            skills=item.skills,
            projects=item.projects,
        )
        for index, item in enumerate(selected[:MAX_MILESTONES])
    ]


async def generate_career_path(role_id: int, confirmed_profile: ConfirmedCVData) -> CareerPathReport:
    gap_report = await explain_role_gap(role_id, confirmed_profile, with_narrative=False)
    current_profile_summary = _profile_summary(confirmed_profile)
    top_gaps = _top_skill_gaps(gap_report)
    allowed_certs = _allowed_certifications(gap_report)
    draft = await _generate_draft(gap_report, current_profile_summary, top_gaps, allowed_certs)
    fallback = _fallback_draft(top_gaps, allowed_certs)

    milestones = _normalize_milestones(draft.milestones, top_gaps)
    readiness_score = gap_report.overall_readiness or gap_report.readiness_score
    return CareerPathReport(
        role_id=gap_report.role_id,
        current_profile_summary=current_profile_summary,
        target_role=gap_report.job_title,
        readiness_score=readiness_score,
        top_gaps=top_gaps,
        milestones=milestones,
        recommended_projects=_unique(
            [*draft.recommended_projects, *(project for item in milestones for project in item.projects)]
        ),
        skills_to_learn=top_gaps,
        certifications=_filter_certifications(draft.certifications, allowed_certs),
        estimated_timeline=timeline_from_readiness(readiness_score),
        requirement_breakdown=gap_report,
    )
