/**
 * Typed client for the Career Compass FastAPI backend.
 */
import { API_BASE_URL } from "./config";

// CV data (parsing)

export type PersonalInfo = {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  current_role: string | null;
  links: string[];
};

export type ProfileSummary = {
  summary: string | null;
  current_seniority_level: string | null;
  years_of_experience: number | null;
};

export type Experience = {
  role: string | null;
  organization: string | null;
  industry: string | null;
  start_date: string | null;
  end_date: string | null;
  duration_months: number | null;
  location: string | null;
  core_responsibilities: string[];
  contextual_skills: string[];
};

export type Education = {
  entry_type: "degree" | "semester_abroad" | "high_school" | "certification" | "other";
  degree_type: string | null;
  field_of_study: string | null;
  institution: string | null;
  start_date: string | null;
  end_date: string | null;
  grade: string | null;
  thesis_title: string | null;
  thesis_grade: string | null;
  courses: string[];
};

export type Project = {
  title: string | null;
  description: string | null;
  organization: string | null;
  role: string | null;
  technologies: string[];
  outcomes: string[];
  links: string[];
  start_date: string | null;
  end_date: string | null;
};

export type Certification = {
  name: string | null;
  issuing_organization: string | null;
  issue_date: string | null;
  expiration_date: string | null;
  credential_id: string | null;
  credential_url: string | null;
};

export type Thesis = {
  title: string | null;
  degree_type: string | null;
  institution: string | null;
  supervisor: string | null;
  description: string | null;
  technologies: string[];
  grade: string | null;
};

export type TechnicalSkill = {
  name: string;
  proficiency_indication: string | null;
};

export type Language = {
  language: string;
  level: string | null;
};

export type InferredSkill = {
  name: string;
  inferred_from: string[];
  rationale: string | null;
};

export type SoftSkill = {
  name: string;
  confidence: number;
};

export type SkillsExtracted = {
  technical_skills: TechnicalSkill[];
  inferred_skills: InferredSkill[];
  soft_skills: SoftSkill[];
  languages: Language[];
};

export type UnmappedInformation = {
  label: string | null;
  value: string;
  source_section: string | null;
  reason_not_mapped: string | null;
};

export type Metadata = {
  parsing_confidence: number;
  detected_language: string | null;
};

export type SourceDocument = {
  filename: string | null;
};

export type CVData = {
  source: SourceDocument | null;
  metadata: Metadata;
  personal_info: PersonalInfo;
  profile_summary: ProfileSummary;
  experience: Experience[];
  education: Education[];
  projects: Project[];
  certifications: Certification[];
  thesis: Thesis[];
  skills_extracted: SkillsExtracted;
  interests: string[];
  potential_direction: string | null;
  unmapped_information: UnmappedInformation[];
};

// Confirmation envelope

export type ConfirmationMetadata = {
  confirmed_at: string;
  confirmed_sections: string[];
  skipped_sections: string[];
  edited_fields: string[];
};

export type ConfirmedCVData = {
  confirmed_cv_data: CVData;
  confirmation_metadata: ConfirmationMetadata;
  career_identity_statement?: string | null;
  career_identity_summary?: CareerIdentitySummary | null;
};

// Profile pipeline

export type CareerIdentitySummary = {
  label: string;
  summary: string;
};

export type EmbeddingProfile = {
  career_identity_summary: CareerIdentitySummary;
  education: Record<string, unknown>[];
  experience: Record<string, unknown>[];
  skills: string[];
  interests: string[];
  certifications: Record<string, unknown>[];
  projects: Record<string, unknown>[];
  potential_direction: string;
};

export type ProfilePipelineResponse = {
  cv_data: CVData;
  privacy_stripped_cv_data: CVData;
  embedding_profile: EmbeddingProfile;
};

// Role matching

export type UserCareerIdentity = {
  title?: string | null;
  summary?: string | null;
};

export type UserEducation = {
  degree?: string | null;
  institution?: string | null;
  start_year?: string | null;
  end_year?: string | null;
};

export type UserExperience = {
  role?: string | null;
  organization?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  summary?: string | null;
  skills: string[];
};

export type UserCertification = {
  name?: string | null;
  issuer?: string | null;
  year?: string | null;
};

export type UserProject = {
  title?: string | null;
  summary?: string | null;
  technologies: string[];
  year?: string | null;
};

export type UserCareerProfile = {
  career_identity: UserCareerIdentity;
  education: UserEducation[];
  experience: UserExperience[];
  skills: string[];
  interests: string[];
  certifications: UserCertification[];
  projects: UserProject[];
  // Inferred from experience/projects, combined with `interests` to build
  // the intent embedding; `career_identity` is now the dedicated source for
  // the identity guardrail embedding instead.
  potential_direction: string;
};

export type RoleMatch = {
  role_id: string | number;
  bucket: string;
  title: string;
  matching_score: number;
  salary: string;
  description: string;
  esco_title: string;
  esco_uri: string;
  matched_skills: string[];
  missing_skills: string[];
  matched_domains: string[];
  matched_certifications: string[];
};

export type RoleMatchResponse = {
  matched_roles: RoleMatch[];
  analysis: string | null;
};

export type DimensionStatus = "strong" | "partial" | "weak";

export type SkillGap = {
  skill: string;
  importance: string;
  domain: string;
  suggestion: string;
  required_skill: string;
  /** Properly-cased display text for required_skill (e.g. "UI/UX Design"
   * where required_skill is the normalized "ui ux design") - display only. */
  display: string;
  user_closest_skill: string | null;
  transferability: number;
  severity: string;
  source: string;
};

export type ActionableSkillGap = {
  skill: string;
  display: string;
  domain: string;
  priority_label: "critical" | "high" | "medium" | "low";
  estimated_effort: "quick_win" | "moderate" | "substantial";
  bridge_skill: string | null;
  why_it_matters: string;
  suggested_action: string;
  proof_to_build: string;
  resume_hint: string;
};

export type SkillDimension = {
  matched_skills: string[];
  missing_skills: string[];
  optional_missing_skills: string[];
  skill_gaps: SkillGap[];
  domain_coverage: Record<string, number>;
  domain_skills: Record<string, string[]>;
  coverage: number;
  status: DimensionStatus;
  summary: string;
};

export type CertificationGap = {
  name: string;
  provider: string | null;
  priority: string;
  reason: string;
  required_certification: string;
  normalized_name: string;
  user_closest_certification: string | null;
  similarity: number;
  status: string;
};

export type CertificationDimension = {
  matched_certifications: string[];
  missing_certifications: CertificationGap[];
  held: string[];
  related: CertificationGap[];
  missing: CertificationGap[];
  coverage: number;
  status: DimensionStatus;
  summary: string;
};

export type SeniorityDimension = {
  user_level: string | null;
  role_level: string | null;
  user_years: number | null;
  gap: string;
  note: string | null;
  summary: string;
};

export type GapNarrative = {
  readiness_summary: string;
  why_this_role: string;
  main_gaps: string;
  next_steps: string;
};

export type GapReport = {
  role_id: string | number;
  job_title: string;
  job_description: string | null;
  domain_tags: string[];
  overall_readiness: number;
  readiness_score: number;
  bucket: string;
  skills: SkillDimension;
  certifications: CertificationDimension;
  seniority: SeniorityDimension;
  grounding_used: string[];
  action_plan: { title: string; description: string; effort: string; priority: string }[];
  top_actionable_skill_gaps?: ActionableSkillGap[];
  narrative: GapNarrative | null;
};

export type CareerPathMilestone = {
  order: number;
  kind: "role" | "skill" | "project" | "certification" | "experience";
  title: string;
  timeline: string;
  rationale: string;
  skills: string[];
  projects: string[];
};

export type CareerPathReport = {
  role_id: string | number;
  plan_summary: string;
  current_profile_summary: string;
  target_role: string;
  readiness_score: number;
  top_gaps: string[];
  milestones: CareerPathMilestone[];
  recommended_projects: string[];
  skills_to_learn: string[];
  certifications: string[];
  estimated_timeline: string;
  requirement_breakdown: GapReport;
};

type CareerResultsV1 = {
  results: RoleMatch[];
};

// Manual CV input

export type ManualEducationInput = {
  degree_type: string;
  institution?: string | null;
  field_of_study?: string | null;
  start_date?: string | null;
  end_date?: string | null;
};

export type ManualExperienceInput = {
  role: string;
  organization?: string | null;
  description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
};

export type ManualProjectInput = {
  title: string;
  description?: string | null;
  technologies?: string[];
  start_date?: string | null;
  end_date?: string | null;
};

export type ManualCertificationInput = {
  name: string;
  issuing_organization?: string | null;
  issue_date?: string | null;
};

export type ManualCVInput = {
  current_role?: string | null;
  seniority_level?: string | null;
  years_of_experience?: number | null;
  summary?: string | null;
  education?: ManualEducationInput[];
  experience?: ManualExperienceInput[];
  technical_skills?: string[];
  soft_skills?: string[];
  languages?: Language[];
  interests?: string[];
  projects?: ManualProjectInput[];
  certifications?: ManualCertificationInput[];
};

// HTTP helpers

const REQUEST_TIMEOUT_MS = 240_000;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(response: Response): Promise<never> {
  let detail = `Request failed with status ${response.status}`;
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string") detail = body.detail;
  } catch {
    // Non-JSON error body; keep the default message.
  }
  throw new ApiError(detail, response.status);
}

/** Upload a PDF CV and run parsing + prompt engineering in one backend pipeline. */
export async function parseCv(file: File): Promise<ProfilePipelineResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/profile-pipeline/parse-cv`, {
    method: "POST",
    body: formData,
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (!response.ok) await parseError(response);
  return response.json();
}

/** Build structured CVData from manual input and run prompt engineering. */
export async function submitManualCv(input: ManualCVInput): Promise<ProfilePipelineResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/profile-pipeline/manual-cv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (!response.ok) await parseError(response);
  return response.json();
}

/** Match a cleaned career profile against the backend RAG pipeline. */
export async function matchRoles(profile: UserCareerProfile, topK = 9): Promise<RoleMatchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/roles/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile,
      top_k: topK,
    }),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (!response.ok) await parseError(response);
  const payload: CareerResultsV1 = await response.json();
  return {
    matched_roles: payload.results,
    analysis: null,
  };
}

/** Build a grounded career roadmap for one selected role and confirmed profile. */
export async function getCareerPath(
  roleId: string | number,
  confirmedProfile: ConfirmedCVData,
): Promise<CareerPathReport> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/roles/${encodeURIComponent(String(roleId))}/career-path`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(confirmedProfile),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    },
  );
  if (!response.ok) await parseError(response);
  return response.json();
}
