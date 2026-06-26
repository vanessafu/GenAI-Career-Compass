/**
 * UI view-model types shared across stages and the store.
 *
 * These are presentation shapes (formerly defined in the deleted mock layer),
 * derived from backend `CVData` / `RoleMatch` via the mappers in `src/lib/`.
 */

/** A skill with a UI-derived confidence (0..100) from its proficiency indication. */
export type AnalyzedSkill = { name: string; confidence: number };

export type ExperienceItem = { role: string; company: string; start: string; end: string };
export type EducationItem = { degree: string; school: string; start: string; end: string };
export type CertificationItem = { name: string; issuer: string; year: string };
export type ProjectItem = { name: string; detail: string; year: string };

/** Career identity shown on the recap screen. */
export type Identity = { archetype: string; lead: string };

export type ManualEducationFormItem = {
  degree: string;
  institution: string;
  fieldOfStudy: string;
  startDate: string;
  endDate: string;
};

export type ManualExperienceFormItem = {
  role: string;
  organization: string;
  startDate: string;
  endDate: string;
};

export type ManualProjectFormItem = {
  title: string;
  description: string;
  technologies: string[];
  startDate: string;
  endDate: string;
};

export type ManualCertificationFormItem = {
  name: string;
  issuingOrganization: string;
  issueDate: string;
};

/** Manual-entry form captured on the entry screen (tier 1 + collapsible tier 2). */
export type ManualProfileForm = {
  // Tier 1 — quick start
  currentRole: string;
  seniorityLevel: string;
  yearsOfExperience: number | null;
  education: ManualEducationFormItem[];
  experience: ManualExperienceFormItem[];
  skills: string[];
  interests: string[];
  targetConstraints: string[];
  // Tier 2 — add more context
  summary: string;
  softSkills: string[];
  languageName: string;
  languageLevel: string;
  projects: ManualProjectFormItem[];
  certifications: ManualCertificationFormItem[];
};

export const emptyManualProfileForm: ManualProfileForm = {
  currentRole: "",
  seniorityLevel: "",
  yearsOfExperience: null,
  education: [],
  experience: [],
  skills: [],
  interests: [],
  targetConstraints: [],
  summary: "",
  softSkills: [],
  languageName: "",
  languageLevel: "",
  projects: [],
  certifications: [],
};

/** A matched role projected for the cards and detail view. */
export type RoleView = {
  id: string;
  title: string;
  trackLabel: string;
  summary: string;
  /** Similarity fit in 0..1. */
  fit: number;
  essentialSkills: string[];
  optionalSkills: string[];
  essentialKnowledge: string[];
  optionalKnowledge: string[];
};
