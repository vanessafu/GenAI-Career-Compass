import type { CareerPathReport, GapReport } from "./api";

type PreparationState = {
  careerPathReports: Record<string, CareerPathReport | unknown>;
  careerPathErrors: Record<string, string | null | undefined>;
  roleGapReports: Record<string, GapReport | unknown>;
  roleGapErrors: Record<string, string | null | undefined>;
};

export function areSelectedPathsPrepared(roleIds: string[], state: PreparationState): boolean {
  return roleIds.every((roleId) => {
    const hasPath = !!state.careerPathReports[roleId] || !!state.careerPathErrors[roleId];
    const hasGap = !!state.roleGapReports[roleId] || !!state.roleGapErrors[roleId];
    return hasPath && hasGap;
  });
}
