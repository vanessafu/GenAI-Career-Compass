/** Map backend RoleMatch records into the UI RoleView shape. */
import type { RoleMatch } from "./api";
import type { RoleView } from "../types";

function clamp01(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

export function roleMatchToView(match: RoleMatch): RoleView {
  return {
    id: match.uri,
    title: match.title,
    trackLabel: match.isco_label?.trim() || "Role",
    summary: match.description?.trim() || "",
    fit: clamp01(match.similarity_score),
    essentialSkills: match.essential_skills,
    optionalSkills: match.optional_skills,
    essentialKnowledge: match.essential_knowledge,
    optionalKnowledge: match.optional_knowledge,
  };
}

export function roleMatchesToViews(matches: RoleMatch[]): RoleView[] {
  return matches.map(roleMatchToView);
}
