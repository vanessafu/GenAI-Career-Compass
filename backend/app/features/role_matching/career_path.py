from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from typing import Iterable

from backend.app.core.openai_client import parse_structured
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.role_matching.gap_analysis import explain_role_gap
from backend.app.features.role_matching.schemas import (
    ActionableSkillGap,
    ActionableSkillGapPolish,
    CareerPathDraft,
    CareerPathLLMDraft,
    CareerPathMilestone,
    CareerPathReport,
    CertificationGap,
    GapReport,
    SkillGap,
)

logger = logging.getLogger("CareerCompass.RoleMatching.CareerPath")

MAX_GAPS = 5
MAX_MILESTONES = 5
SINGLE_TIMELINE_RE = re.compile(r"^\s*(\d+)\s*(weeks?|months?)\s*$", re.IGNORECASE)

_CAREER_PATH_SYSTEM_PROMPT = """
Role: Career roadmap writer.

Task: Convert a precomputed gap report into a concise, evidence-grounded career path.

Use only supplied role requirements, readiness score, matched skills, skill gaps,
certification gaps, role description, timeline range, and actionable gap drafts.

Output rules:
- plan_summary: 2-3 conversational sentences to the user. Mention closeness,
  matched skills, and main gaps. Do not repeat current_profile_summary or list
  milestones/certifications.
- milestones: 3-5 items. kind must be exactly one of role, skill, project,
  certification, experience.
- Set each milestone timeline as a single duration: "1 week" to "4 weeks" for
  short work; whole "month"/"months" values after that. Do not output ranges,
  calendar windows, cumulative timelines, plus signs, or vague text.
- Keep milestone durations roughly within target_timeline_range; estimated_timeline
  is computed by the API.
- certifications: only names from certification_gaps.
- top_skill_gap_suggestions: optional polish for supplied top_actionable_skill_gaps
  only. Do not add, remove, rename, or reorder gaps; suggestion.skill must exactly
  match a supplied skill. Keep fields one concise sentence; preserve priority and effort.

Never invent certifications, salaries, job markets, courses, bootcamps, user
experience, or unsupported career claims.
""".strip()


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


# Weeks-per-tier, named after and thresholded the same as the /match buckets
# (0.70/0.35 mirrors gap_analysis._status()'s strong/partial/weak cutoffs)
# so a role graded "strong" reads as a Ready Now-style 1-3 month plan, etc.
_TIMELINE_RANGES_WEEKS: dict[str, tuple[int, int]] = {
    "ready_now": (4, 12),  # 1-3 months
    "next_step": (12, 20),  # 3-5 months
    "aspirational": (20, 32),  # 5-8 months
}


def readiness_tier(readiness: float | None) -> str:
    score = max(0.0, min(1.0, float(readiness or 0.0)))
    if score >= 0.70:
        return "ready_now"
    if score >= 0.35:
        return "next_step"
    return "aspirational"


def _format_month_range(low_weeks: int, high_weeks: int) -> str:
    return f"{low_weeks // 4}-{high_weeks // 4} months"


def timeline_from_readiness(readiness: float | None) -> str:
    low, high = _TIMELINE_RANGES_WEEKS[readiness_tier(readiness)]
    return _format_month_range(low, high)


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
    return _clean(gap.display or gap.required_skill or gap.skill)


_IMPORTANCE_RANK = {"essential": 0, "important": 1, "nice_to_have": 2, "": 3}


def _top_skill_gaps(report: GapReport) -> list[str]:
    """Career-path display groups gaps at the domain level (e.g. "Backend",
    "DevOps") instead of individual skills - everything else (matched_skills,
    missing_skills, the LLM prompt payload's per-skill detail, etc.) still
    works with specific skills. Roles never reprocessed with the domain
    hierarchy (gap.domain empty) fall back to using the skill name itself as
    its own pseudo-domain so career path still has something to show."""
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    domain_gaps: dict[str, list[SkillGap]] = defaultdict(list)
    for gap in report.skills.skill_gaps:
        domain_gaps[gap.domain or _skill_name(gap)].append(gap)

    def domain_rank(domain: str) -> tuple[int, int, float]:
        gaps = domain_gaps[domain]
        best_importance = min(_IMPORTANCE_RANK.get(gap.importance, 3) for gap in gaps)
        best_severity = min(severity_rank.get(gap.severity, 3) for gap in gaps)
        avg_transferability = sum(gap.transferability for gap in gaps) / len(gaps)
        return (best_importance, best_severity, avg_transferability)

    ordered_domains = sorted(domain_gaps, key=domain_rank)
    return _unique(ordered_domains)[:MAX_GAPS]


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


def _fallback_draft(
    gaps: list[str],
    allowed_certs: list[str],
    matched_skills: list[str] | None = None,
) -> CareerPathDraft:
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
            timeline="4 weeks",
            rationale=f"This directly addresses the visible {gap} gap.",
            skills=[gap],
            projects=[f"Create a small project that demonstrates {gap}"],
        )
        for index, gap in enumerate(targets)
    ]

    return CareerPathDraft(
        plan_summary=_fallback_plan_summary(gaps, allowed_certs, matched_skills or []),
        milestones=milestones,
        recommended_projects=_unique(project for item in milestones for project in item.projects),
        estimated_timeline=_format_duration_weeks(4 * len(milestones)) if milestones else "4 weeks",
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


def _fallback_plan_summary(
    gaps: list[str],
    allowed_certs: list[str],
    matched_skills: list[str] | None = None,
) -> str:
    matched = _unique((matched_skills or [])[:3])
    matched_text = (
        f"your existing {', '.join(matched)} experience already gives you useful overlap"
        if matched
        else "your existing background already gives you some useful overlap"
    )
    if gaps:
        gap_text = ", ".join(gaps[:3])
        return (
            f"You're not starting from zero here: {matched_text}. "
            f"The main stretch is building clearer strength in {gap_text}, so the next steps should make that progress easy to see."
        )
    return (
        f"You're already close to this direction, and {matched_text}. "
        "The next steps should mostly sharpen the evidence so the fit is easy to recognize."
    )


def _format_duration(value: int, unit: str) -> str:
    label = unit[:-1] if value == 1 and unit.endswith("s") else unit
    return f"{value} {label}"


def _format_duration_weeks(weeks: int) -> str:
    weeks = max(0, int(weeks))
    if weeks <= 4:
        return _format_duration(weeks, "weeks")
    return _format_duration((weeks + 3) // 4, "months")


def _duration_weeks(timeline: str) -> int | None:
    match = SINGLE_TIMELINE_RE.match(_clean(timeline))
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2).lower()
    return value * 4 if unit.startswith("month") else value


def _display_timeline(timeline: str, fallback: str = "4 weeks") -> str:
    weeks = _duration_weeks(timeline)
    return _format_duration_weeks(weeks) if weeks is not None else fallback


def _estimated_timeline(readiness: float | None) -> str:
    """Always the readiness tier's fixed range (Ready Now 1-3mo / Next Step
    3-5mo / Aspirational 5-8mo) - a deterministic function of readiness alone,
    not a sum of the LLM's individual milestone durations (those stay
    per-milestone-granular, but no longer drive the headline estimate)."""
    return timeline_from_readiness(readiness)


def _summary_matches_profile(summary: str, current_profile_summary: str) -> bool:
    summary_key = _clean(summary).casefold()
    profile_key = _clean(current_profile_summary).casefold()
    return bool(profile_key and (summary_key == profile_key or summary_key.startswith(profile_key)))


def _plan_summary(draft: CareerPathDraft, fallback: CareerPathDraft, current_profile_summary: str) -> str:
    summary = _clean(draft.plan_summary)
    if summary and not _summary_matches_profile(summary, current_profile_summary):
        return summary
    return fallback.plan_summary


def _prompt_payload(
    report: GapReport,
    current_profile_summary: str,
    top_gaps: list[str],
    allowed_certs: list[str],
) -> dict:
    readiness = report.overall_readiness or report.readiness_score
    return {
        "current_profile_summary": current_profile_summary,
        "target_role": report.job_title,
        "readiness_score": round(readiness, 3),
        "target_timeline_range": timeline_from_readiness(readiness),
        "top_gaps": top_gaps,
        "matched_skills": report.skills.matched_skills[:10],
        "certification_gaps": allowed_certs,
        "allowed_milestone_kinds": ["role", "skill", "project", "certification", "experience"],
        "seniority": report.seniority.model_dump(mode="json"),
        "role_description": _clean(report.job_description)[:1200],
        "top_actionable_skill_gaps": _top_gap_polish_payload(report),
    }


def _top_gap_polish_payload(report: GapReport) -> list[dict[str, str]]:
    return [
        {
            "skill": gap.skill,
            "display": gap.display,
            "domain": gap.domain,
            "priority_label": gap.priority_label,
            "estimated_effort": gap.estimated_effort,
            "bridge_skill": gap.bridge_skill or "",
            "draft_why_it_matters": gap.why_it_matters,
            "draft_suggested_action": gap.suggested_action,
            "draft_proof_to_build": gap.proof_to_build,
            "draft_resume_hint": gap.resume_hint,
        }
        for gap in report.top_actionable_skill_gaps[:3]
    ]


async def _generate_draft(
    report: GapReport,
    current_profile_summary: str,
    top_gaps: list[str],
    allowed_certs: list[str],
) -> CareerPathDraft:
    try:
        draft = await parse_structured(
            messages=[
                {"role": "system", "content": _CAREER_PATH_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        _prompt_payload(report, current_profile_summary, top_gaps, allowed_certs),
                        ensure_ascii=False,
                    ),
                },
            ],
            response_format=CareerPathLLMDraft,
            model_purpose="career_path",
        )
        if draft is not None:
            return draft
    except Exception as exc:
        logger.warning("Career path generation failed; using deterministic fallback: %s", exc)
    return _fallback_draft(top_gaps, allowed_certs, report.skills.matched_skills[:3])


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

    fallback_timelines = [item.timeline for item in fallback]

    return [
        CareerPathMilestone(
            order=index + 1,
            kind=item.kind,
            title=item.title,
            timeline=_display_timeline(
                item.timeline,
                fallback_timelines[index] if index < len(fallback_timelines) else "4 weeks",
            ),
            rationale=item.rationale,
            skills=item.skills,
            projects=item.projects,
        )
        for index, item in enumerate(selected[:MAX_MILESTONES])
    ]


def _apply_top_gap_polish(
    gaps: list[ActionableSkillGap],
    suggestions: list[ActionableSkillGapPolish],
) -> None:
    by_skill = {_clean(gap.skill): gap for gap in gaps}
    for suggestion in suggestions:
        gap = by_skill.get(_clean(suggestion.skill))
        if gap is None:
            continue
        if _clean(suggestion.why_it_matters):
            gap.why_it_matters = _clean(suggestion.why_it_matters)
        if _clean(suggestion.suggested_action):
            gap.suggested_action = _clean(suggestion.suggested_action)
        if _clean(suggestion.proof_to_build):
            gap.proof_to_build = _clean(suggestion.proof_to_build)
        if _clean(suggestion.resume_hint):
            gap.resume_hint = _clean(suggestion.resume_hint)


def _sync_skill_gap_suggestions(report: GapReport) -> None:
    suggestions = {gap.skill: gap.suggested_action for gap in report.top_actionable_skill_gaps}
    for gap in report.skills.skill_gaps:
        polished = suggestions.get(gap.required_skill)
        if polished:
            gap.suggestion = polished


async def generate_career_path(role_id: int, confirmed_profile: ConfirmedCVData) -> CareerPathReport:
    gap_report = await explain_role_gap(role_id, confirmed_profile, with_narrative=False)
    current_profile_summary = _profile_summary(confirmed_profile)
    top_gaps = _top_skill_gaps(gap_report)
    allowed_certs = _allowed_certifications(gap_report)
    draft = await _generate_draft(gap_report, current_profile_summary, top_gaps, allowed_certs)
    fallback = _fallback_draft(top_gaps, allowed_certs, gap_report.skills.matched_skills[:3])

    milestones = _normalize_milestones(draft.milestones, top_gaps)
    readiness_score = gap_report.overall_readiness or gap_report.readiness_score
    _apply_top_gap_polish(
        gap_report.top_actionable_skill_gaps,
        getattr(draft, "top_skill_gap_suggestions", []),
    )
    _sync_skill_gap_suggestions(gap_report)
    return CareerPathReport(
        role_id=gap_report.role_id,
        plan_summary=_plan_summary(draft, fallback, current_profile_summary),
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
        estimated_timeline=_estimated_timeline(readiness_score),
        requirement_breakdown=gap_report,
    )
