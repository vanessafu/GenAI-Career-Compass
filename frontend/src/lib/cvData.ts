/**
 * Helpers that bridge the backend CV schema and the editable UI view-models.
 *
 *   - manual entry form  -> CVData
 *   - CVData             -> Recap view-models (skills, experience, ...)
 *   - Recap edits        -> CVData (so edits flow into matching/identity)
 *   - CVData             -> ConfirmedCVData envelope (mirrors backend helper)
 */
import type {
  CVData,
  ConfirmedCVData,
  Education,
  Experience,
  ManualCVInput,
  Project,
  UserCareerProfile,
} from "./api";
import type {
  AnalyzedSkill,
  CertificationItem,
  EducationItem,
  ExperienceItem,
  Identity,
  ManualProfileForm,
  ProjectItem,
} from "../types";

/** All CVData sections, used when assembling the ConfirmedCVData envelope. */
const CV_SECTIONS = [
  "personal_info",
  "profile_summary",
  "experience",
  "education",
  "projects",
  "certifications",
  "thesis",
  "skills_extracted",
  "interests",
] as const;

const MAX_ITEMS = 50;
const MAX_SHORT_TEXT_LENGTH = 200;
const MAX_LONG_TEXT_LENGTH = 5_000;

/** Recap editable lists, kept in the store and merged back into CVData. */
export type RecapEdits = {
  skills: AnalyzedSkill[];
  interests: string[];
  experiences: ExperienceItem[];
  educations: EducationItem[];
  certifications: CertificationItem[];
  projects: ProjectItem[];
};

/* ───────────────────────────  Manual entry  ────────────────────────────── */

/** Build the backend manual-entry DTO from the tiered entry form. */
export function manualFormToInput(form: ManualProfileForm): ManualCVInput {
  const languages = form.languages
    .filter((item) => item.name.trim())
    .map((item) => ({ language: item.name.trim(), level: item.level.trim() || null }));

  return {
    current_role: form.currentRole.trim() || null,
    summary: form.summary.trim() || null,
    education: form.education
      .filter((item) => item.degree.trim())
      .map((item) => ({
        degree_type: item.degree.trim(),
        institution: item.institution.trim() || null,
        field_of_study: item.fieldOfStudy.trim() || null,
        start_date: item.startDate.trim() || null,
        end_date: item.endDate.trim() || null,
      })),
    experience: form.experience
      .filter((item) => item.role.trim())
      .map((item) => ({
        role: item.role.trim(),
        organization: item.organization.trim() || null,
        description: item.description.trim() || null,
        start_date: item.startDate.trim() || null,
        end_date: item.endDate.trim() || null,
      })),
    technical_skills: form.skills.map((s) => s.trim()).filter(Boolean),
    soft_skills: form.softSkills.map((s) => s.trim()).filter(Boolean),
    languages,
    interests: form.interests.map((s) => s.trim()).filter(Boolean),
    projects: form.projects
      .filter((item) => item.title.trim())
      .map((item) => ({
        title: item.title.trim(),
        description: item.description.trim() || null,
        technologies: item.technologies.map((s) => s.trim()).filter(Boolean),
        start_date: item.startDate.trim() || null,
        end_date: item.endDate.trim() || null,
      })),
    certifications: form.certifications
      .filter((item) => item.name.trim())
      .map((item) => ({
        name: item.name.trim(),
        issuing_organization: item.issuingOrganization.trim() || null,
        issue_date: item.issueDate.trim() || null,
      })),
  };
}

/* ───────────────────────────  CVData -> view  ──────────────────────────── */

const PROFICIENCY_SCORE: { match: string; score: number }[] = [
  { match: "expert", score: 90 },
  { match: "advanced", score: 80 },
  { match: "intermediate", score: 70 },
  { match: "beginner", score: 50 },
];

/** Map a free-text proficiency indication to a 0..100 confidence for the UI. */
export function deriveConfidence(proficiency: string | null | undefined): number {
  if (!proficiency) return 65;
  const lower = proficiency.toLowerCase();
  const hit = PROFICIENCY_SCORE.find((p) => lower.includes(p.match));
  return hit ? hit.score : 65;
}

function dateOr(date: string | null | undefined, fallback = "—"): string {
  return date || fallback;
}

export function cvDataToSkills(cv: CVData): AnalyzedSkill[] {
  return cv.skills_extracted.technical_skills.map((s) => ({
    name: s.name,
    confidence: deriveConfidence(s.proficiency_indication),
  }));
}

export function cvDataToExperiences(cv: CVData): ExperienceItem[] {
  return cv.experience.map((e, sourceIndex) => ({
    sourceIndex,
    role: e.role ?? "Role",
    company: e.organization ?? "—",
    summary: joinedLongText(e.core_responsibilities ?? []) ?? "",
    start: dateOr(e.start_date),
    end: dateOr(e.end_date, "Present"),
  }));
}

export function cvDataToEducations(cv: CVData): EducationItem[] {
  return cv.education.map((e, sourceIndex) => ({
    sourceIndex,
    degree: e.degree_type ?? "",
    field: e.field_of_study ?? "",
    school: e.institution ?? "—",
    start: dateOr(e.start_date),
    end: dateOr(e.end_date),
  }));
}

export function cvDataToCertifications(cv: CVData): CertificationItem[] {
  return cv.certifications.map((c, sourceIndex) => ({
    sourceIndex,
    name: c.name ?? "Certification",
    issuer: c.issuing_organization ?? "—",
    year: dateOr(c.issue_date),
  }));
}

export function cvDataToProjects(cv: CVData): ProjectItem[] {
  return cv.projects.map((p, sourceIndex) => ({
    sourceIndex,
    name: p.title ?? "Project",
    detail: p.description ?? "—",
    technologies: (p.technologies ?? []).map((t) => t.trim()).filter(Boolean),
    start: dateOr(p.start_date),
    end: dateOr(p.end_date),
  }));
}

export function cvDataToRecapEdits(cv: CVData): RecapEdits {
  return {
    skills: cvDataToSkills(cv),
    interests: normalizeInterests(cv.interests),
    experiences: cvDataToExperiences(cv),
    educations: cvDataToEducations(cv),
    certifications: cvDataToCertifications(cv),
    projects: cvDataToProjects(cv),
  };
}

/** Derive a short identity archetype from CV fields (fallback before/without LLM). */
export function deriveArchetype(cv: CVData): string {
  const role = cv.personal_info.current_role?.trim();
  const seniority = cv.profile_summary.current_seniority_level?.trim();
  if (role && seniority) return `${seniority} ${role}`;
  if (role) return role;
  if (seniority) return `${seniority} professional`;
  return "Emerging professional";
}

export function fallbackIdentity(cv: CVData): Identity {
  return {
    archetype: deriveArchetype(cv),
    lead: cv.profile_summary.summary?.trim() || "We mapped your profile to realistic next roles.",
  };
}

function textOrNull(value: string | null | undefined): string | null {
  const cleaned = value?.trim();
  if (!cleaned || cleaned === "Present" || !/[A-Za-z0-9]/.test(cleaned)) return null;
  return cleaned;
}

function boundedText(value: string | null | undefined, maxLength: number): string | null {
  const cleaned = textOrNull(value);
  return cleaned?.slice(0, maxLength) ?? null;
}

function shortTextOrNull(value: string | null | undefined): string | null {
  return boundedText(value, MAX_SHORT_TEXT_LENGTH);
}

function longTextOrNull(value: string | null | undefined): string | null {
  return boundedText(value, MAX_LONG_TEXT_LENGTH);
}

function yearOrNull(value: string | null | undefined): string | null {
  const cleaned = textOrNull(value);
  if (!cleaned) return null;
  return cleaned.match(/\d{4}/)?.[0] ?? cleaned.slice(0, MAX_SHORT_TEXT_LENGTH);
}

function uniqueText(values: Iterable<string | null | undefined>): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const cleaned = textOrNull(value);
    if (!cleaned) continue;
    const key = cleaned.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(cleaned);
  }
  return out;
}

function boundedTextList(values: Iterable<string | null | undefined>): string[] {
  return uniqueText(values)
    .map((value) => value.slice(0, MAX_SHORT_TEXT_LENGTH))
    .slice(0, MAX_ITEMS);
}

function joinedLongText(values: Iterable<string | null | undefined>): string | null {
  return longTextOrNull(uniqueText(values).join("; "));
}

function normalizeInterests(values: Iterable<string | null | undefined>): string[] {
  return boundedTextList(Array.from(values).flatMap((value) => (value ?? "").split(/[,;\n]/)));
}

/** Project edited CVData into the clean profile schema expected by role matching. */
export function cvDataToUserCareerProfile(
  cv: CVData,
  identity: Identity | null,
): UserCareerProfile {
  const fallback = fallbackIdentity(cv);
  const skills = boundedTextList([
    ...cv.skills_extracted.technical_skills.map((skill) => skill.name),
    ...cv.skills_extracted.inferred_skills.map((skill) => skill.name),
    ...cv.skills_extracted.soft_skills.map((skill) => skill.name),
  ]);

  return {
    career_identity: {
      title:
        shortTextOrNull(identity?.archetype) ??
        shortTextOrNull(fallback.archetype) ??
        "Emerging professional",
      summary:
        longTextOrNull(identity?.lead) ??
        longTextOrNull(cv.profile_summary.summary) ??
        longTextOrNull(fallback.lead) ??
        "We mapped your profile to realistic next roles.",
    },
    education: cv.education.map((item) => ({
      degree: shortTextOrNull(uniqueText([item.degree_type, item.field_of_study]).join(" in ")),
      institution: null,
      start_year: yearOrNull(item.start_date),
      end_year: yearOrNull(item.end_date),
    })),
    experience: cv.experience.map((item) => ({
      role: shortTextOrNull(item.role),
      organization: null,
      start_date: shortTextOrNull(item.start_date),
      end_date: shortTextOrNull(item.end_date),
      summary: joinedLongText(item.core_responsibilities),
      skills: boundedTextList(item.contextual_skills),
    })),
    skills,
    interests: normalizeInterests(cv.interests),
    potential_direction: longTextOrNull(cv.potential_direction) ?? "",
    certifications: cv.certifications.map((item) => ({
      name: shortTextOrNull(item.name),
      issuer: shortTextOrNull(item.issuing_organization),
      year: yearOrNull(item.issue_date),
    })),
    projects: cv.projects.map((item) => ({
      title: shortTextOrNull(item.title),
      summary: joinedLongText([item.description, ...item.outcomes]),
      technologies: boundedTextList(item.technologies),
      year: yearOrNull(item.start_date ?? item.end_date),
    })),
  };
}

/* ───────────────────────────  view -> CVData  ──────────────────────────── */

/** Merge edited recap lists back into a base CVData, preserving unedited fields. */
export function applyEditsToCvData(base: CVData, edits: RecapEdits): CVData {
  const experience: Experience[] = edits.experiences.map((e) => ({
    ...(e.sourceIndex === undefined
      ? emptyExperience()
      : (base.experience[e.sourceIndex] ?? emptyExperience())),
    role: e.role,
    organization: e.company,
    core_responsibilities: e.summary?.trim()
      ? [e.summary.trim().slice(0, MAX_LONG_TEXT_LENGTH)]
      : [],
    start_date: e.start === "—" ? null : e.start,
    end_date: e.end === "Present" || e.end === "—" ? null : e.end,
  }));

  const education: Education[] = edits.educations.map((e) => ({
    ...(e.sourceIndex === undefined
      ? emptyEducation()
      : (base.education[e.sourceIndex] ?? emptyEducation())),
    degree_type: e.degree.trim() || null,
    field_of_study: e.field.trim() || null,
    institution: e.school,
    start_date: e.start === "—" ? null : e.start,
    end_date: e.end === "—" ? null : e.end,
  }));

  const projects: Project[] = edits.projects.map((p) => ({
    ...(p.sourceIndex === undefined
      ? emptyProject()
      : (base.projects[p.sourceIndex] ?? emptyProject())),
    title: p.name,
    description: p.detail === "—" ? null : longTextOrNull(p.detail),
    technologies: p.technologies ?? [],
    start_date: p.start === "—" ? null : p.start.trim() || null,
    end_date: p.end === "—" ? null : p.end.trim() || null,
  }));

  return {
    ...base,
    personal_info: base.personal_info,
    experience,
    education,
    projects,
    certifications: edits.certifications.map((c) => ({
      ...(c.sourceIndex === undefined
        ? {
            name: null,
            issuing_organization: null,
            issue_date: null,
            expiration_date: null,
            credential_id: null,
            credential_url: null,
          }
        : (base.certifications[c.sourceIndex] ?? {
            name: null,
            issuing_organization: null,
            issue_date: null,
            expiration_date: null,
            credential_id: null,
            credential_url: null,
          })),
      name: c.name,
      issuing_organization: c.issuer === "—" ? null : c.issuer,
      issue_date: c.year === "—" ? null : c.year,
    })),
    skills_extracted: {
      ...base.skills_extracted,
      technical_skills: edits.skills.map((s) => {
        const existing = base.skills_extracted.technical_skills.find((t) => t.name === s.name);
        return { name: s.name, proficiency_indication: existing?.proficiency_indication ?? null };
      }),
    },
    interests: normalizeInterests(edits.interests),
  };
}

function emptyExperience(): Experience {
  return {
    role: null,
    organization: null,
    industry: null,
    start_date: null,
    end_date: null,
    duration_months: null,
    location: null,
    core_responsibilities: [],
    contextual_skills: [],
  };
}

function emptyEducation(): Education {
  return {
    entry_type: "degree",
    degree_type: null,
    field_of_study: null,
    institution: null,
    start_date: null,
    end_date: null,
    grade: null,
    thesis_title: null,
    thesis_grade: null,
    courses: [],
  };
}

function emptyProject(): Project {
  return {
    title: null,
    description: null,
    organization: null,
    role: null,
    technologies: [],
    outcomes: [],
    links: [],
    start_date: null,
    end_date: null,
  };
}

/* ───────────────────────────  Confirmation  ────────────────────────────── */

/** Wrap a CVData in the ConfirmedCVData envelope (mirrors backend to_confirmed_cv_data). */
export function toConfirmedCvData(cvData: CVData, identity?: Identity | null): ConfirmedCVData {
  const fallback = fallbackIdentity(cvData);
  const label =
    shortTextOrNull(identity?.archetype) ??
    shortTextOrNull(fallback.archetype) ??
    "Emerging professional";
  const summary =
    longTextOrNull(identity?.lead) ??
    longTextOrNull(fallback.lead) ??
    "We mapped your profile to realistic next roles.";

  return {
    confirmed_cv_data: cvData,
    confirmation_metadata: {
      confirmed_at: new Date().toISOString(),
      confirmed_sections: [...CV_SECTIONS],
      skipped_sections: [],
      edited_fields: [],
    },
    career_identity_statement: longTextOrNull(`${label}: ${summary}`),
    career_identity_summary: { label, summary },
  };
}
