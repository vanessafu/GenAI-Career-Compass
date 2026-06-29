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
    seniority_level: form.seniorityLevel.trim() || null,
    years_of_experience: form.yearsOfExperience,
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
    target_constraints: form.targetConstraints.map((s) => s.trim()).filter(Boolean),
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

function yearOrNull(value: string | null | undefined): string | null {
  const cleaned = textOrNull(value);
  if (!cleaned) return null;
  return cleaned.match(/\d{4}/)?.[0] ?? cleaned;
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

function normalizeInterests(values: Iterable<string | null | undefined>): string[] {
  return uniqueText(Array.from(values).flatMap((value) => (value ?? "").split(/[,;\n]/)));
}

function targetPreferences(cv: CVData): string[] {
  return uniqueText(
    cv.unmapped_information
      .filter((item) => item.label === "target_constraint")
      .map((item) => item.value),
  );
}

export function identityLeadWithTargetPreferences(
  cv: CVData,
  lead: string | null | undefined,
): string {
  const base = textOrNull(lead) ?? fallbackIdentity(cv).lead;
  const preferences = targetPreferences(cv);
  if (preferences.length === 0) return base;

  const line = `Target preferences: ${preferences.join(", ")}`;
  return base.includes(line) ? base : `${base}\n\n${line}`;
}

/** Project edited CVData into the clean profile schema expected by role matching. */
export function cvDataToUserCareerProfile(
  cv: CVData,
  identity: Identity | null,
): UserCareerProfile {
  const fallback = fallbackIdentity(cv);
  const skills = uniqueText([
    ...cv.skills_extracted.technical_skills.map((skill) => skill.name),
    ...cv.skills_extracted.soft_skills,
  ]);

  return {
    career_identity: {
      title: textOrNull(identity?.archetype) ?? fallback.archetype,
      summary:
        textOrNull(identity?.lead) ?? textOrNull(cv.profile_summary.summary) ?? fallback.lead,
    },
    education: cv.education.map((item) => ({
      degree: uniqueText([item.degree_type, item.field_of_study]).join(" in ") || null,
      institution: null,
      start_year: yearOrNull(item.start_date),
      end_year: yearOrNull(item.end_date),
    })),
    experience: cv.experience.map((item) => ({
      role: textOrNull(item.role),
      organization: null,
      start_date: textOrNull(item.start_date),
      end_date: textOrNull(item.end_date),
      summary: uniqueText(item.core_responsibilities).join("; ") || null,
      skills: uniqueText(item.contextual_skills),
    })),
    skills,
    interests: normalizeInterests(cv.interests),
    certifications: cv.certifications.map((item) => ({
      name: textOrNull(item.name),
      issuer: null,
      year: yearOrNull(item.issue_date),
    })),
    projects: cv.projects.map((item) => ({
      title: textOrNull(item.title),
      summary:
        uniqueText([item.description, item.outcomes.length ? item.outcomes.join("; ") : null]).join(
          "; ",
        ) || null,
      technologies: uniqueText(item.technologies),
      year: yearOrNull(item.start_date ?? item.end_date),
    })),
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
  const label = textOrNull(identity?.archetype) ?? fallback.archetype;
  const summary = textOrNull(identity?.lead) ?? fallback.lead;

  return {
    confirmed_cv_data: cvData,
    confirmation_metadata: {
      confirmed_at: new Date().toISOString(),
      confirmed_sections: [...CV_SECTIONS],
      skipped_sections: [],
      edited_fields: [],
    },
    career_identity_statement: `${label}: ${summary}`,
    career_identity_summary: { label, summary },
  };
}
