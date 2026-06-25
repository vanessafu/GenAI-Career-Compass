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

export type SkillsExtracted = {
  technical_skills: TechnicalSkill[];
  soft_skills: string[];
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
  extracted_text: string | null;
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
};

export type RoleMatch = {
  uri: string;
  isco_group: string | null;
  isco_label: string | null;
  title: string;
  alt_labels: string[];
  description: string | null;
  essential_knowledge: string[];
  essential_skills: string[];
  optional_knowledge: string[];
  optional_skills: string[];
  similarity_score: number;
};

export type RoleMatchResponse = {
  query_text: string;
  matched_roles: RoleMatch[];
  analysis: string | null;
};

type CareerResultV1 = {
  bucket: string;
  title: string;
  matching_score: number;
  salary: string;
  description: string;
  matched_skills: string[];
  missing_skills: string[];
  matched_domains: string[];
  matched_certifications: string[];
};

type CareerResultsV1 = {
  results: CareerResultV1[];
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
  start_date?: string | null;
  end_date?: string | null;
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
};

// HTTP helpers

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

function bucketLabel(bucket: string): string {
  const label = bucket
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  return label || "Role";
}

function resultToRoleMatch(result: CareerResultV1, index: number): RoleMatch {
  return {
    uri: `${result.bucket}:${result.title}:${index}`,
    isco_group: result.bucket,
    isco_label: bucketLabel(result.bucket),
    title: result.title,
    alt_labels: result.salary ? [result.salary] : [],
    description: result.description || null,
    essential_knowledge: result.matched_domains,
    essential_skills: result.matched_skills,
    optional_knowledge: result.matched_certifications,
    optional_skills: result.missing_skills,
    similarity_score: Math.max(0, Math.min(1, result.matching_score / 100)),
  };
}

/** Upload a PDF CV and run parsing + prompt engineering in one backend pipeline. */
export async function parseCv(file: File): Promise<ProfilePipelineResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/v1/profile-pipeline/parse-cv`, {
    method: "POST",
    body: formData,
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
  });
  if (!response.ok) await parseError(response);
  return response.json();
}

/** Match a cleaned career profile against the backend RAG pipeline. */
export async function matchRoles(profile: UserCareerProfile, topK = 6): Promise<RoleMatchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/roles/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile,
      top_k: topK,
      mode: "balanced",
      include_debug: false,
    }),
  });
  if (!response.ok) await parseError(response);
  const payload: CareerResultsV1 = await response.json();
  return {
    query_text: "",
    matched_roles: payload.results.map(resultToRoleMatch),
    analysis: null,
  };
}
