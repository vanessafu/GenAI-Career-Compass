import type {
  AnalyzedSkill,
  CertificationItem,
  EducationItem,
  ExperienceItem,
  ProjectItem,
} from "@/types";

type RecapSections = {
  educations: EducationItem[];
  experiences: ExperienceItem[];
  skills: AnalyzedSkill[];
  interests: string[];
  certifications: CertificationItem[];
  projects: ProjectItem[];
};

function hasText(value: string | null | undefined, fallback?: string): boolean {
  const text = value?.trim();
  if (!text || text === "\u2014" || text === "-") return false;
  return text.toLowerCase() !== fallback?.toLowerCase();
}

export function buildMissingBigSections(sections: RecapSections): string[] {
  const missing: string[] = [];

  if (
    !sections.educations.some((item) => hasText(item.degree, "Education") || hasText(item.school))
  ) {
    missing.push("education");
  }
  if (!sections.experiences.some((item) => hasText(item.role, "Role") || hasText(item.company))) {
    missing.push("experience");
  }
  if (!sections.skills.some((item) => hasText(item.name))) missing.push("skills");
  if (!sections.interests.some((item) => hasText(item))) missing.push("interests");
  if (!sections.certifications.some((item) => hasText(item.name, "Certification"))) {
    missing.push("certifications");
  }
  if (!sections.projects.some((item) => hasText(item.name, "Project"))) {
    missing.push("projects");
  }

  return missing;
}
