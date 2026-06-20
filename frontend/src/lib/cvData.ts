/**
 * Helpers that bridge the backend CV schema and the editable UI view-models.
 *
 *   - manual entry form  -> CVData
 *   - CVData             -> Recap view-models (skills, experience, ...)
 *   - Recap edits        -> CVData (so edits flow into matching/identity)
 *   - CVData             -> ConfirmedCVData envelope (mirrors backend helper)
 */
import type { CVData, ConfirmedCVData, Education, Experience, ManualCVInput, Project } from "./api";
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
  const languages = form.languageName.trim()
    ? [{ language: form.languageName.trim(), level: form.languageLevel.trim() || null }]
    : [];

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
        start_date: item.startDate.trim() || null,
        end_date: item.endDate.trim() || null,
      })),
    technical_skills: form.skills.map((s) => s.trim()).filter(Boolean),
    soft_skills: form.softSkills.map((s) => s.trim()).filter(Boolean),
    languages,
    interests: form.interests.map((s) => s.trim()).filter(Boolean),
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

/** Extract a 4-digit year from an ISO-ish date string, or fall back to the raw value. */
function yearOf(date: string | null | undefined, fallback = "—"): string {
  if (!date) return fallback;
  const match = date.match(/\d{4}/);
  return match ? match[0] : date;
}

export function cvDataToSkills(cv: CVData): AnalyzedSkill[] {
  return cv.skills_extracted.technical_skills.map((s) => ({
    name: s.name,
    confidence: deriveConfidence(s.proficiency_indication),
  }));
}

export function cvDataToExperiences(cv: CVData): ExperienceItem[] {
  return cv.experience.map((e) => ({
    role: e.role ?? "Role",
    company: e.organization ?? "—",
    start: yearOf(e.start_date),
    end: yearOf(e.end_date, "Present"),
  }));
}

export function cvDataToEducations(cv: CVData): EducationItem[] {
  return cv.education.map((e) => ({
    degree: e.degree_type ?? e.field_of_study ?? "Education",
    school: e.institution ?? "—",
    start: yearOf(e.start_date),
    end: yearOf(e.end_date),
  }));
}

export function cvDataToCertifications(cv: CVData): CertificationItem[] {
  return cv.certifications.map((c) => ({
    name: c.name ?? "Certification",
    issuer: c.issuing_organization ?? "—",
    year: yearOf(c.issue_date),
  }));
}

export function cvDataToProjects(cv: CVData): ProjectItem[] {
  return cv.projects.map((p) => ({
    name: p.title ?? "Project",
    detail: p.description ?? "—",
    year: yearOf(p.start_date ?? p.end_date),
  }));
}

export function cvDataToRecapEdits(cv: CVData): RecapEdits {
  return {
    skills: cvDataToSkills(cv),
    interests: [...cv.interests],
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

/* ───────────────────────────  view -> CVData  ──────────────────────────── */

/** Merge edited recap lists back into a base CVData, preserving unedited fields. */
export function applyEditsToCvData(base: CVData, edits: RecapEdits): CVData {
  const experience: Experience[] = edits.experiences.map((e, i) => ({
    ...(base.experience[i] ?? emptyExperience()),
    role: e.role,
    organization: e.company,
    start_date: e.start === "—" ? null : e.start,
    end_date: e.end === "Present" || e.end === "—" ? null : e.end,
  }));

  const education: Education[] = edits.educations.map((e, i) => ({
    ...(base.education[i] ?? emptyEducation()),
    degree_type: e.degree,
    institution: e.school,
    start_date: e.start === "—" ? null : e.start,
    end_date: e.end === "—" ? null : e.end,
  }));

  const projects: Project[] = edits.projects.map((p, i) => ({
    ...(base.projects[i] ?? emptyProject()),
    title: p.name,
    description: p.detail === "—" ? null : p.detail,
    start_date: p.year === "—" ? null : p.year,
  }));

  return {
    ...base,
    personal_info: base.personal_info,
    experience,
    education,
    projects,
    certifications: edits.certifications.map((c, i) => ({
      ...(base.certifications[i] ?? {
        name: null,
        issuing_organization: null,
        issue_date: null,
        expiration_date: null,
        credential_id: null,
        credential_url: null,
      }),
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
    interests: [...edits.interests],
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
export function toConfirmedCvData(cvData: CVData): ConfirmedCVData {
  return {
    confirmed_cv_data: cvData,
    confirmation_metadata: {
      confirmed_at: new Date().toISOString(),
      confirmed_sections: [...CV_SECTIONS],
      skipped_sections: [],
      edited_fields: [],
    },
  };
}
