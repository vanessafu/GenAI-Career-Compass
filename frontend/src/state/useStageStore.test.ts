import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CareerPathReport, CVData, RoleMatchResponse } from "@/lib/api";

const api = vi.hoisted(() => ({
  getCareerPath: vi.fn(),
  matchRoles: vi.fn(),
  parseCv: vi.fn(),
  submitManualCv: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {},
  ...api,
}));

import { cvDataToRecapEdits } from "@/lib/cvData";
import { useStageStore } from "./useStageStore";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function cv(currentRole: string): CVData {
  return {
    source: null,
    metadata: { parsing_confidence: 1, detected_language: "en" },
    personal_info: {
      full_name: null,
      email: null,
      phone: null,
      location: null,
      current_role: currentRole,
      links: [],
    },
    profile_summary: {
      summary: `${currentRole} profile`,
      current_seniority_level: null,
      years_of_experience: null,
    },
    experience: [],
    education: [],
    projects: [],
    certifications: [],
    thesis: [],
    skills_extracted: {
      technical_skills: [],
      inferred_skills: [],
      soft_skills: [],
      languages: [],
    },
    interests: [],
    potential_direction: null,
    unmapped_information: [],
  };
}

function seed(profile: CVData) {
  useStageStore.setState({ cvData: profile, ...cvDataToRecapEdits(profile) });
}

beforeEach(() => {
  useStageStore.getState().reset();
  api.getCareerPath.mockReset();
  api.matchRoles.mockReset();
});

describe("request ownership", () => {
  it("ignores stale matching results without clearing the replacement request", async () => {
    const oldRequest = deferred<RoleMatchResponse>();
    const newRequest = deferred<RoleMatchResponse>();
    api.matchRoles.mockReturnValueOnce(oldRequest.promise).mockReturnValueOnce(newRequest.promise);

    seed(cv("Old"));
    const stale = useStageStore.getState().runMatching();
    useStageStore.getState().reset();
    seed(cv("New"));
    const current = useStageStore.getState().runMatching();

    oldRequest.resolve({
      matched_roles: [{ role_id: "old" }],
      analysis: null,
    } as RoleMatchResponse);
    await stale;
    void useStageStore.getState().runMatching();

    expect(api.matchRoles).toHaveBeenCalledTimes(2);
    expect(useStageStore.getState().roleMatches).toEqual([]);

    newRequest.resolve({
      matched_roles: [{ role_id: "new" }],
      analysis: null,
    } as RoleMatchResponse);
    await current;
    expect(useStageStore.getState().roleMatches[0]?.role_id).toBe("new");
  });

  it("uses the generated identity for matching", async () => {
    api.matchRoles.mockResolvedValue({ matched_roles: [], analysis: null });
    seed(cv("Current"));
    const identity = {
      archetype: "Platform builder",
      lead: "Designs reliable developer platforms.",
    };
    useStageStore.setState({ identity });

    await useStageStore.getState().runMatching();

    expect(api.matchRoles).toHaveBeenCalledWith(
      expect.objectContaining({
        career_identity: { title: identity.archetype, summary: identity.lead },
      }),
      9,
    );
    expect(useStageStore.getState().identity).toEqual(identity);
  });

  it("clears stale matches and paths when returning to recap", () => {
    useStageStore.setState({
      roleMatches: [{ role_id: "1" }] as RoleMatchResponse["matched_roles"],
      selectedRoleIds: ["1"],
      careerPathReports: { "1": { role_id: "1" } as CareerPathReport },
      careerPathLoading: { "1": true },
      careerPathErrors: { "1": "stale" },
    });

    useStageStore.getState().setStage("recap");
    expect(useStageStore.getState()).toMatchObject({
      stage: "recap",
      roleMatches: [],
      selectedRoleIds: [],
      careerPathReports: {},
      careerPathLoading: {},
      careerPathErrors: {},
    });
  });

  it("loads one career-path request per unique role and ignores a late path after reset", async () => {
    api.getCareerPath.mockImplementation(
      async (roleId: string) =>
        ({
          role_id: roleId,
        }) as CareerPathReport,
    );
    seed(cv("Current"));

    await useStageStore.getState().prepareSelectedPaths(["1", "2", "2", "3"]);
    expect(api.getCareerPath).toHaveBeenCalledTimes(3);
    expect(Object.keys(useStageStore.getState().careerPathReports)).toEqual(["1", "2", "3"]);

    const latePath = deferred<CareerPathReport>();
    api.getCareerPath.mockReturnValueOnce(latePath.promise);
    const pending = useStageStore.getState().loadCareerPath("4");
    useStageStore.getState().reset();
    latePath.resolve({ role_id: "4" } as CareerPathReport);
    await pending;
    expect(useStageStore.getState().careerPathReports).toEqual({});
  });
});
