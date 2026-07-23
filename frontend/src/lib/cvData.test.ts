import { describe, expect, it } from "vitest";
import type { CVData } from "./api";
import {
  applyEditsToCvData,
  cvDataToRecapEdits,
  cvDataToUserCareerProfile,
  toConfirmedCvData,
} from "./cvData";

const baseCv = {
  personal_info: { current_role: "Engineer" },
  profile_summary: { summary: "Builds products", current_seniority_level: null },
  experience: [
    { role: "First", industry: "first-industry", start_date: "2020-01-15" },
    {
      role: "Second",
      industry: "second-industry",
      start_date: "2023-05-17",
      end_date: "2024-06-20",
      core_responsibilities: [],
    },
  ],
  education: [
    { degree_type: "First", grade: "first-grade" },
    {
      degree_type: "Second",
      grade: "second-grade",
      start_date: "2021-09-01",
      end_date: "2023-07-31",
    },
  ],
  projects: [
    { title: "First", links: ["first-link"] },
    {
      title: "Second",
      links: ["second-link"],
      technologies: [],
      start_date: "2022-02-12",
      end_date: "2022-11-30",
    },
  ],
  certifications: [
    { name: "First", credential_id: "first-id" },
    { name: "Second", credential_id: "second-id", issue_date: "2024-03-14" },
  ],
  skills_extracted: { technical_skills: [], inferred_skills: [], soft_skills: [], languages: [] },
  interests: [],
} as unknown as CVData;

describe("recap CV mapping", () => {
  it("keeps source metadata and exact dates after deleting earlier rows", () => {
    const edits = cvDataToRecapEdits(baseCv);
    edits.experiences.shift();
    edits.educations.shift();
    edits.projects.shift();
    edits.certifications.shift();
    edits.experiences.push({
      role: "New",
      company: "New company",
      summary: "",
      start: "2025-01",
      end: "Present",
    });

    const result = applyEditsToCvData(baseCv, edits);

    expect(result.experience[0]).toMatchObject({
      role: "Second",
      industry: "second-industry",
      start_date: "2023-05-17",
      end_date: "2024-06-20",
    });
    expect(result.experience[1]).toMatchObject({ role: "New", industry: null });
    expect(result.education[0]).toMatchObject({
      degree_type: "Second",
      grade: "second-grade",
      start_date: "2021-09-01",
      end_date: "2023-07-31",
    });
    expect(result.projects[0]).toMatchObject({
      title: "Second",
      links: ["second-link"],
      start_date: "2022-02-12",
      end_date: "2022-11-30",
    });
    expect(result.certifications[0]).toMatchObject({
      name: "Second",
      credential_id: "second-id",
      issue_date: "2024-03-14",
    });
  });

  it("keeps every derived API payload within backend bounds", () => {
    const boundedCv = {
      ...baseCv,
      personal_info: { current_role: "R".repeat(200) },
      profile_summary: { summary: "S".repeat(5_000), current_seniority_level: "L".repeat(200) },
      experience: [
        {
          role: "Engineer",
          core_responsibilities: ["A".repeat(5_000), "B".repeat(5_000)],
          contextual_skills: [],
        },
      ],
      education: [{ degree_type: "D".repeat(200), field_of_study: "F".repeat(200) }],
      projects: [
        {
          title: "Project",
          description: "P".repeat(5_000),
          outcomes: ["O".repeat(5_000)],
          technologies: [],
          links: [],
        },
      ],
      certifications: [],
      skills_extracted: {
        technical_skills: Array.from({ length: 50 }, (_, index) => ({
          name: `Technical ${index}`,
        })),
        inferred_skills: Array.from({ length: 50 }, (_, index) => ({
          name: `Inferred ${index}`,
        })),
        soft_skills: Array.from({ length: 50 }, (_, index) => ({ name: `Soft ${index}` })),
        languages: [],
      },
      interests: Array.from({ length: 50 }, (_, index) => `Interest ${index}a, Interest ${index}b`),
      potential_direction: "T".repeat(5_000),
    } as unknown as CVData;
    const identity = { archetype: "I".repeat(200), lead: "J".repeat(5_000) };

    const profile = cvDataToUserCareerProfile(boundedCv, identity);
    expect(profile.skills).toHaveLength(50);
    expect(profile.interests).toHaveLength(50);
    expect(profile.education[0].degree).toHaveLength(200);
    expect(profile.experience[0].summary).toHaveLength(5_000);
    expect(profile.projects[0].summary).toHaveLength(5_000);

    const confirmed = toConfirmedCvData(boundedCv, identity);
    expect(confirmed.career_identity_summary?.label).toHaveLength(200);
    expect(confirmed.career_identity_summary?.summary).toHaveLength(5_000);
    expect(confirmed.career_identity_statement).toHaveLength(5_000);

    const edits = cvDataToRecapEdits(boundedCv);
    edits.experiences[0].summary = "X".repeat(6_000);
    edits.projects[0].detail = "Y".repeat(6_000);
    const edited = applyEditsToCvData(boundedCv, edits);
    expect(edited.experience[0].core_responsibilities[0]).toHaveLength(5_000);
    expect(edited.projects[0].description).toHaveLength(5_000);
  });
});
