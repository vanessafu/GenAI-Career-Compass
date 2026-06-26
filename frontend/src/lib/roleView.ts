/** Map backend RoleMatch records into the UI RoleView shape. */
import type { RoleMatch } from "./api";
import type { RoleView } from "../types";

function clamp01(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function bucketLabel(bucket: string): string {
  const label = bucket
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  return label || "Role";
}

export function roleMatchToView(match: RoleMatch): RoleView {
  const label = bucketLabel(match.bucket);
  return {
    id: String(match.role_id),
    title: match.title,
    bucket: match.bucket,
    bucketLabel: label,
    trackLabel: label,
    summary: match.description?.trim() || "",
    fit: clamp01(match.matching_score / 100),
    salary: match.salary?.trim() || "",
    escoTitle: match.esco_title?.trim() || "",
    escoUri: match.esco_uri?.trim() || "",
    matchedSkills: match.matched_skills,
    missingSkills: match.missing_skills,
    essentialSkills: match.matched_skills,
    optionalSkills: [],
    essentialKnowledge: match.matched_domains,
    optionalKnowledge: match.matched_certifications,
  };
}

export function roleMatchesToViews(matches: RoleMatch[]): RoleView[] {
  return matches.map(roleMatchToView);
}
