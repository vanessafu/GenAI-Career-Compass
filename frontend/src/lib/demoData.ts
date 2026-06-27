import type {
  CareerPathMilestone,
  CareerPathReport,
  CVData,
  CertificationDimension,
  CertificationGap,
  DimensionStatus,
  EmbeddingProfile,
  GapReport,
  RoleMatch,
  SkillDimension,
  SkillGap,
} from "./api";
import type { Identity } from "@/types";

export const DEMO_IDENTITY: Identity = {
  archetype: "Senior Backend Platform Engineer",
  lead: "Senior backend engineer with strong evidence in API ownership, PostgreSQL-backed services, cloud deployment, and production reliability. The profile points toward platform engineering or senior backend roles where service ownership, developer tooling, and operational quality are central.",
};

export const DEMO_CV_DATA: CVData = {
  source: {
    filename: "demo-platform-engineer-cv.pdf",
    extracted_text: null,
  },
  metadata: {
    parsing_confidence: 0.98,
    detected_language: "en",
  },
  personal_info: {
    full_name: "Mara Fischer",
    email: "mara.fischer@example.com",
    phone: null,
    location: "Berlin, Germany",
    current_role: "Senior Backend Engineer",
    links: ["https://github.com/marafischer", "https://linkedin.com/in/marafischer"],
  },
  profile_summary: {
    summary:
      "Builds reliable backend platforms for product teams, with depth in TypeScript, Python, PostgreSQL, cloud infrastructure, and observability.",
    current_seniority_level: "Senior",
    years_of_experience: 7,
  },
  experience: [
    {
      role: "Senior Backend Engineer",
      organization: "Northstar Health",
      industry: "Health technology",
      start_date: "2022-03",
      end_date: null,
      duration_months: 52,
      location: "Berlin",
      core_responsibilities: [
        "Owned appointment and billing APIs serving multiple product teams.",
        "Led PostgreSQL query tuning and service reliability improvements.",
        "Introduced observability dashboards and incident review practices.",
      ],
      contextual_skills: [
        "TypeScript",
        "Node.js",
        "Python",
        "PostgreSQL",
        "Docker",
        "AWS ECS",
        "OpenTelemetry",
      ],
    },
    {
      role: "Backend Engineer",
      organization: "Atlas Logistics",
      industry: "Logistics",
      start_date: "2019-01",
      end_date: "2022-02",
      duration_months: 37,
      location: "Hamburg",
      core_responsibilities: [
        "Built event-driven integrations for warehouse and carrier systems.",
        "Migrated legacy REST services to containerized deployments.",
      ],
      contextual_skills: ["Java", "Spring Boot", "Kafka", "REST APIs", "GitHub Actions"],
    },
    {
      role: "Junior Software Developer",
      organization: "Blueleaf Studio",
      industry: "SaaS",
      start_date: "2017-06",
      end_date: "2018-12",
      duration_months: 18,
      location: "Cologne",
      core_responsibilities: ["Shipped internal tooling and customer-facing dashboard features."],
      contextual_skills: ["React", "SQL", "Git", "Testing"],
    },
  ],
  education: [
    {
      entry_type: "degree",
      degree_type: "MSc",
      field_of_study: "Computer Science",
      institution: "TU Berlin",
      start_date: "2015",
      end_date: "2017",
      grade: "1.5",
      thesis_title: "Reliable message processing in distributed logistics systems",
      thesis_grade: "1.3",
      courses: ["Distributed Systems", "Databases", "Software Architecture"],
    },
    {
      entry_type: "degree",
      degree_type: "BSc",
      field_of_study: "Information Systems",
      institution: "University of Cologne",
      start_date: "2011",
      end_date: "2015",
      grade: "1.8",
      thesis_title: null,
      thesis_grade: null,
      courses: ["Algorithms", "Web Engineering", "Statistics"],
    },
  ],
  projects: [
    {
      title: "Self-service deployment portal",
      description:
        "Internal portal that lets product teams deploy services with standardized runtime, secrets, and observability defaults.",
      organization: "Northstar Health",
      role: "Technical lead",
      technologies: ["TypeScript", "PostgreSQL", "AWS ECS", "GitHub Actions"],
      outcomes: ["Reduced deployment handoffs", "Improved service ownership"],
      links: [],
      start_date: "2024",
      end_date: null,
    },
    {
      title: "API reliability scorecards",
      description:
        "Service health dashboards combining latency, error budget, incident, and ownership data.",
      organization: "Northstar Health",
      role: "Engineer",
      technologies: ["OpenTelemetry", "Prometheus", "Grafana", "Python"],
      outcomes: ["Made reliability gaps visible to engineering managers"],
      links: [],
      start_date: "2023",
      end_date: null,
    },
  ],
  certifications: [
    {
      name: "AWS Certified Developer - Associate",
      issuing_organization: "Amazon Web Services",
      issue_date: "2023",
      expiration_date: null,
      credential_id: null,
      credential_url: null,
    },
    {
      name: "Professional Scrum Master I",
      issuing_organization: "Scrum.org",
      issue_date: "2021",
      expiration_date: null,
      credential_id: null,
      credential_url: null,
    },
  ],
  thesis: [
    {
      title: "Reliable message processing in distributed logistics systems",
      degree_type: "MSc",
      institution: "TU Berlin",
      supervisor: null,
      description:
        "Compared retry, deduplication, and queueing strategies for distributed service workflows.",
      technologies: ["Java", "PostgreSQL", "RabbitMQ"],
      grade: "1.3",
    },
  ],
  skills_extracted: {
    technical_skills: [
      { name: "TypeScript", proficiency_indication: "advanced" },
      { name: "Node.js", proficiency_indication: "advanced" },
      { name: "Python", proficiency_indication: "advanced" },
      { name: "PostgreSQL", proficiency_indication: "advanced" },
      { name: "REST APIs", proficiency_indication: "expert" },
      { name: "Docker", proficiency_indication: "advanced" },
      { name: "AWS ECS", proficiency_indication: "intermediate" },
      { name: "OpenTelemetry", proficiency_indication: "intermediate" },
      { name: "Kafka", proficiency_indication: "intermediate" },
      { name: "GitHub Actions", proficiency_indication: "intermediate" },
    ],
    soft_skills: ["Mentoring", "Incident facilitation", "Cross-team communication"],
    languages: [
      { language: "English", level: "C1" },
      { language: "German", level: "Native" },
    ],
  },
  interests: ["platform engineering", "cloud architecture", "developer experience", "reliability"],
  unmapped_information: [
    {
      label: "target_constraint",
      value: "Prefer backend/platform roles with visible technical ownership.",
      source_section: "profile",
      reason_not_mapped: "Target preference used for role intent.",
    },
    {
      label: "target_constraint",
      value: "Open to hybrid Berlin or remote EU teams.",
      source_section: "profile",
      reason_not_mapped: "Location preference used for presentation only.",
    },
  ],
};

export const DEMO_EMBEDDING_PROFILE: EmbeddingProfile = {
  career_identity_summary: {
    label: DEMO_IDENTITY.archetype,
    summary: DEMO_IDENTITY.lead,
  },
  education: DEMO_CV_DATA.education,
  experience: DEMO_CV_DATA.experience,
  skills: DEMO_CV_DATA.skills_extracted.technical_skills.map((skill) => skill.name),
  interests: DEMO_CV_DATA.interests,
  certifications: DEMO_CV_DATA.certifications,
  projects: DEMO_CV_DATA.projects,
};

export const DEMO_ROLE_MATCHES = [
  role(
    "demo-platform-engineer",
    "ready_now",
    "Platform Engineer",
    95,
    "Builds the shared infrastructure, deployment workflows, and developer tooling that help product teams ship reliable services.",
    ["TypeScript", "Docker", "AWS ECS", "GitHub Actions", "PostgreSQL"],
    ["Kubernetes", "Infrastructure as Code"],
    ["platform_engineering", "devops", "software_engineering"],
  ),
  role(
    "demo-backend-engineer",
    "ready_now",
    "Senior Backend Engineer",
    93,
    "Owns core APIs, data flows, service boundaries, and production quality for backend-heavy product teams.",
    ["REST APIs", "Node.js", "Python", "PostgreSQL", "Testing"],
    ["Domain-driven design", "Service ownership metrics"],
    ["software_engineering", "backend", "data_engineering"],
  ),
  role(
    "demo-api-integration-engineer",
    "ready_now",
    "API Integration Engineer",
    90,
    "Designs and operates robust integrations between internal services, partner APIs, and event-driven workflows.",
    ["REST APIs", "Kafka", "Java", "GitHub Actions", "SQL"],
    ["Contract testing", "Integration monitoring"],
    ["software_engineering", "automation_scripting"],
  ),
  role(
    "demo-cloud-solutions-architect",
    "next_step",
    "Cloud Solutions Architect",
    86,
    "Turns product and platform needs into pragmatic cloud architectures, migration plans, and operational standards.",
    ["AWS ECS", "Docker", "PostgreSQL", "System Design"],
    ["AWS Well-Architected", "Infrastructure as Code"],
    ["cloud", "architecture", "devops"],
  ),
  role(
    "demo-devops-engineer",
    "next_step",
    "DevOps Engineer",
    83,
    "Automates delivery pipelines, deployment environments, reliability checks, and the operational path from code to production.",
    ["Docker", "GitHub Actions", "AWS ECS", "OpenTelemetry"],
    ["Kubernetes", "Terraform"],
    ["devops", "platform_engineering", "qa_testing"],
  ),
  role(
    "demo-sre",
    "next_step",
    "Site Reliability Engineer",
    79,
    "Uses observability, incident practice, and automation to improve service reliability and reduce operational risk.",
    ["OpenTelemetry", "Prometheus", "Incident facilitation", "Python"],
    ["SLO design", "Chaos engineering"],
    ["devops", "software_engineering"],
  ),
  role(
    "demo-engineering-manager",
    "aspirational",
    "Engineering Manager",
    73,
    "Leads a product engineering team through delivery, coaching, technical tradeoffs, and cross-functional planning.",
    ["Mentoring", "Cross-team communication", "Service ownership"],
    ["Performance management", "Hiring"],
    ["management", "software_engineering"],
  ),
  role(
    "demo-security-engineer",
    "aspirational",
    "Application Security Engineer",
    68,
    "Improves secure software delivery through threat modeling, code review, secure defaults, and developer enablement.",
    ["Backend engineering", "API design", "Cloud deployment"],
    ["Threat modeling", "OWASP ASVS", "Security testing"],
    ["cybersecurity", "software_engineering"],
  ),
  role(
    "demo-data-platform-engineer",
    "aspirational",
    "Data Platform Engineer",
    64,
    "Builds reliable data ingestion, transformation, orchestration, and quality foundations for analytics and ML teams.",
    ["PostgreSQL", "Python", "Kafka", "Service reliability"],
    ["Airflow", "Data modeling", "Data quality checks"],
    ["data_engineering", "software_engineering"],
  ),
] satisfies RoleMatch[];

export const DEMO_SELECTED_ROLE_IDS = [
  "demo-platform-engineer",
  "demo-cloud-solutions-architect",
  "demo-devops-engineer",
];

const roleDescriptions = Object.fromEntries(
  DEMO_ROLE_MATCHES.map((match) => [String(match.role_id), match.description]),
);

export const DEMO_GAP_REPORTS = {
  "demo-platform-engineer": gapReport({
    roleId: "demo-platform-engineer",
    jobTitle: "Platform Engineer",
    bucket: "ready_now",
    readiness: 0.86,
    domains: ["platform_engineering", "devops", "software_engineering"],
    matched: ["TypeScript", "Docker", "AWS ECS", "GitHub Actions", "PostgreSQL"],
    gaps: [
      skillGap("Kubernetes", "Docker and AWS ECS", 0.55, "medium"),
      skillGap("Infrastructure as Code", "GitHub Actions deployment work", 0.45, "medium"),
      skillGap("Developer portal ownership", "Self-service deployment portal", 0.7, "low"),
    ],
    certifications: [],
  }),
  "demo-backend-engineer": gapReport({
    roleId: "demo-backend-engineer",
    jobTitle: "Senior Backend Engineer",
    bucket: "ready_now",
    readiness: 0.9,
    domains: ["software_engineering", "backend", "data_engineering"],
    matched: ["REST APIs", "Node.js", "Python", "PostgreSQL", "Testing"],
    gaps: [
      skillGap("Domain-driven design", "API service ownership", 0.58, "medium"),
      skillGap("Service ownership metrics", "Reliability scorecards", 0.66, "low"),
    ],
    certifications: [],
  }),
  "demo-api-integration-engineer": gapReport({
    roleId: "demo-api-integration-engineer",
    jobTitle: "API Integration Engineer",
    bucket: "ready_now",
    readiness: 0.84,
    domains: ["software_engineering", "automation_scripting"],
    matched: ["REST APIs", "Kafka", "Java", "GitHub Actions", "SQL"],
    gaps: [
      skillGap("Contract testing", "REST API testing", 0.52, "medium"),
      skillGap("Integration monitoring", "OpenTelemetry dashboards", 0.62, "low"),
    ],
    certifications: [],
  }),
  "demo-cloud-solutions-architect": gapReport({
    roleId: "demo-cloud-solutions-architect",
    jobTitle: "Cloud Solutions Architect",
    bucket: "next_step",
    readiness: 0.72,
    domains: ["cloud", "architecture", "devops"],
    matched: ["AWS ECS", "Docker", "PostgreSQL", "System Design"],
    gaps: [
      skillGap("AWS Well-Architected", "AWS ECS production work", 0.4, "high"),
      skillGap("Infrastructure as Code", "GitHub Actions deployment work", 0.45, "medium"),
      skillGap("Migration planning", "Container migration experience", 0.5, "medium"),
    ],
    certifications: [certGap("AWS Certified Solutions Architect - Associate", "AWS")],
  }),
  "demo-devops-engineer": gapReport({
    roleId: "demo-devops-engineer",
    jobTitle: "DevOps Engineer",
    bucket: "next_step",
    readiness: 0.69,
    domains: ["devops", "platform_engineering", "qa_testing"],
    matched: ["Docker", "GitHub Actions", "AWS ECS", "OpenTelemetry"],
    gaps: [
      skillGap("Kubernetes", "Docker and AWS ECS", 0.48, "high"),
      skillGap("Terraform", "GitHub Actions deployment work", 0.35, "high"),
      skillGap("Release governance", "Service ownership", 0.6, "medium"),
    ],
    certifications: [certGap("HashiCorp Terraform Associate", "HashiCorp")],
  }),
  "demo-sre": gapReport({
    roleId: "demo-sre",
    jobTitle: "Site Reliability Engineer",
    bucket: "next_step",
    readiness: 0.66,
    domains: ["devops", "software_engineering"],
    matched: ["OpenTelemetry", "Prometheus", "Incident facilitation", "Python"],
    gaps: [
      skillGap("SLO design", "API reliability scorecards", 0.5, "high"),
      skillGap("Error budget policy", "Incident review practices", 0.46, "medium"),
      skillGap("Chaos engineering", null, 0.1, "medium"),
    ],
    certifications: [],
  }),
  "demo-engineering-manager": gapReport({
    roleId: "demo-engineering-manager",
    jobTitle: "Engineering Manager",
    bucket: "aspirational",
    readiness: 0.58,
    domains: ["management", "software_engineering"],
    matched: ["Mentoring", "Cross-team communication", "Technical leadership"],
    gaps: [
      skillGap("Performance management", "Mentoring", 0.35, "high"),
      skillGap("Hiring process ownership", null, 0.1, "high"),
      skillGap("Team planning", "Cross-team delivery", 0.48, "medium"),
    ],
    certifications: [],
    seniorityGap: "under",
  }),
  "demo-security-engineer": gapReport({
    roleId: "demo-security-engineer",
    jobTitle: "Application Security Engineer",
    bucket: "aspirational",
    readiness: 0.52,
    domains: ["cybersecurity", "software_engineering"],
    matched: ["Backend engineering", "API design", "Cloud deployment"],
    gaps: [
      skillGap("Threat modeling", "System design", 0.32, "high"),
      skillGap("OWASP ASVS", null, 0.12, "high"),
      skillGap("Security testing", "API testing", 0.42, "medium"),
    ],
    certifications: [certGap("CSSLP", "ISC2")],
  }),
  "demo-data-platform-engineer": gapReport({
    roleId: "demo-data-platform-engineer",
    jobTitle: "Data Platform Engineer",
    bucket: "aspirational",
    readiness: 0.49,
    domains: ["data_engineering", "software_engineering"],
    matched: ["PostgreSQL", "Python", "Kafka", "Service reliability"],
    gaps: [
      skillGap("Airflow", null, 0.08, "high"),
      skillGap("Data modeling", "PostgreSQL schema design", 0.46, "medium"),
      skillGap("Data quality checks", "Backend testing", 0.38, "medium"),
    ],
    certifications: [],
  }),
} satisfies Record<string, GapReport>;

export const DEMO_CAREER_PATH_REPORTS = {
  "demo-platform-engineer": pathReport(
    "demo-platform-engineer",
    "3 months",
    [
      milestone(1, "skill", "Ship one Kubernetes-backed service", "3 weeks", [
        "Kubernetes",
        "Service deployment",
      ]),
      milestone(2, "project", "Add Terraform to the deployment portal", "4 weeks", [
        "Infrastructure as Code",
      ]),
      milestone(3, "experience", "Run a platform enablement pilot", "4 weeks", [
        "Developer experience",
      ]),
    ],
    ["Add Terraform-backed environment provisioning to the self-service deployment portal."],
    [],
  ),
  "demo-backend-engineer": pathReport(
    "demo-backend-engineer",
    "2 months",
    [
      milestone(1, "project", "Document service boundaries for a core API", "2 weeks", [
        "Domain-driven design",
      ]),
      milestone(2, "experience", "Add ownership scorecards to two services", "3 weeks", [
        "Service ownership metrics",
      ]),
      milestone(3, "skill", "Practice architecture review facilitation", "2 weeks", [
        "Technical leadership",
      ]),
    ],
    ["Publish an API ownership review with metrics, risks, and next actions."],
    [],
  ),
  "demo-api-integration-engineer": pathReport(
    "demo-api-integration-engineer",
    "2 months",
    [
      milestone(1, "skill", "Add consumer-driven contract tests", "3 weeks", ["Contract testing"]),
      milestone(2, "project", "Create an integration health dashboard", "3 weeks", [
        "Integration monitoring",
      ]),
      milestone(3, "experience", "Lead a partner API migration review", "2 weeks", [
        "API governance",
      ]),
    ],
    ["Build a partner API sandbox with contract tests and alerting."],
    [],
  ),
  "demo-cloud-solutions-architect": pathReport(
    "demo-cloud-solutions-architect",
    "5 months",
    [
      milestone(1, "certification", "AWS Solutions Architect Associate", "2 months", [
        "AWS Well-Architected",
      ]),
      milestone(2, "project", "Design a reference architecture for one product area", "4 weeks", [
        "Cloud architecture",
      ]),
      milestone(3, "experience", "Facilitate a migration planning workshop", "4 weeks", [
        "Migration planning",
      ]),
      milestone(4, "skill", "Write infrastructure as code for the reference stack", "4 weeks", [
        "Infrastructure as Code",
      ]),
    ],
    ["Create a Well-Architected migration proposal for one existing service."],
    ["AWS Certified Solutions Architect - Associate"],
  ),
  "demo-devops-engineer": pathReport(
    "demo-devops-engineer",
    "4 months",
    [
      milestone(1, "skill", "Build a Terraform module for service infrastructure", "4 weeks", [
        "Terraform",
      ]),
      milestone(2, "skill", "Deploy a service to Kubernetes", "4 weeks", ["Kubernetes"]),
      milestone(3, "project", "Create a release checklist with automated gates", "3 weeks", [
        "Release governance",
      ]),
      milestone(4, "certification", "Terraform Associate prep", "4 weeks", ["Terraform"]),
    ],
    ["Rebuild one existing ECS deployment as a Terraform-managed Kubernetes service."],
    ["HashiCorp Terraform Associate"],
  ),
  "demo-sre": pathReport(
    "demo-sre",
    "3 months",
    [
      milestone(1, "skill", "Define SLOs for a high-traffic API", "3 weeks", ["SLO design"]),
      milestone(2, "project", "Add error budget reporting", "4 weeks", ["Error budget policy"]),
      milestone(3, "experience", "Run a game day for one service", "3 weeks", [
        "Chaos engineering",
      ]),
      milestone(4, "experience", "Lead an incident review improvement", "2 weeks", [
        "Incident practice",
      ]),
    ],
    ["Turn the API reliability scorecard into an SLO and error budget dashboard."],
    [],
  ),
  "demo-engineering-manager": pathReport(
    "demo-engineering-manager",
    "9 months",
    [
      milestone(1, "experience", "Mentor two engineers with explicit growth goals", "2 months", [
        "Coaching",
      ]),
      milestone(2, "skill", "Own quarterly planning for a small platform stream", "2 months", [
        "Team planning",
      ]),
      milestone(3, "experience", "Shadow hiring and performance calibration", "2 months", [
        "Hiring",
        "Performance management",
      ]),
      milestone(4, "role", "Acting Tech Lead or Staff Engineer scope", "3 months", ["Leadership"]),
    ],
    ["Run a team health and delivery planning retro with measurable follow-up actions."],
    [],
  ),
  "demo-security-engineer": pathReport(
    "demo-security-engineer",
    "5 months",
    [
      milestone(1, "skill", "Complete OWASP ASVS fundamentals", "4 weeks", ["OWASP ASVS"]),
      milestone(2, "project", "Threat-model a production API", "3 weeks", ["Threat modeling"]),
      milestone(3, "project", "Add secure defaults to service templates", "2 months", [
        "Security testing",
      ]),
      milestone(4, "experience", "Partner with security on one review", "4 weeks", [
        "Application security",
      ]),
    ],
    ["Write a threat model and security test plan for the appointment API."],
    ["CSSLP"],
  ),
  "demo-data-platform-engineer": pathReport(
    "demo-data-platform-engineer",
    "5 months",
    [
      milestone(1, "skill", "Build an Airflow DAG for a small data product", "4 weeks", [
        "Airflow",
      ]),
      milestone(2, "project", "Model an analytics-ready event stream", "4 weeks", [
        "Data modeling",
      ]),
      milestone(3, "project", "Add data quality checks and alerting", "4 weeks", [
        "Data quality checks",
      ]),
      milestone(4, "experience", "Pair with analytics on a production data pipeline", "2 months", [
        "Data engineering",
      ]),
    ],
    ["Create a reliability-tracked ingestion pipeline from Kafka to PostgreSQL analytics tables."],
    [],
  ),
} satisfies Record<string, CareerPathReport>;

function role(
  roleId: string,
  bucket: RoleMatch["bucket"],
  title: string,
  score: number,
  description: string,
  matchedSkills: string[],
  missingSkills: string[],
  matchedDomains: string[],
): RoleMatch {
  return {
    role_id: roleId,
    bucket,
    title,
    matching_score: score,
    salary: "EUR 70k-95k",
    description,
    esco_title: title,
    esco_uri: `demo:${roleId}`,
    matched_skills: matchedSkills,
    missing_skills: missingSkills,
    matched_domains: matchedDomains,
    matched_certifications: ["AWS Certified Developer - Associate"],
  };
}

function skillGap(
  requiredSkill: string,
  closestSkill: string | null,
  transferability: number,
  severity: SkillGap["severity"],
): SkillGap {
  const bridge = closestSkill
    ? `The profile has adjacent ${closestSkill} evidence; add direct ${requiredSkill} proof to make the transfer clearer.`
    : `${requiredSkill} is not visible in the profile yet. Add a concrete work example, project, or training artifact.`;

  return {
    skill: requiredSkill,
    importance: severity,
    suggestion: bridge,
    required_skill: requiredSkill,
    user_closest_skill: closestSkill,
    transferability,
    severity,
    source: "demo_fixture",
  };
}

function certGap(name: string, provider: string): CertificationGap {
  return {
    name,
    provider,
    priority: "recommended",
    reason:
      "This credential would make the missing certification signal easier to verify for this role.",
    required_certification: name,
    normalized_name: name.toLowerCase(),
    user_closest_certification: "AWS Certified Developer - Associate",
    similarity: 0.35,
    status: "missing",
  };
}

function gapReport({
  roleId,
  jobTitle,
  bucket,
  readiness,
  domains,
  matched,
  gaps,
  certifications,
  seniorityGap = "match",
}: {
  roleId: string;
  jobTitle: string;
  bucket: GapReport["bucket"];
  readiness: number;
  domains: string[];
  matched: string[];
  gaps: SkillGap[];
  certifications: CertificationGap[];
  seniorityGap?: string;
}): GapReport {
  const missing = gaps.map((gap) => gap.required_skill);
  return {
    role_id: roleId,
    job_title: jobTitle,
    job_description: roleDescriptions[roleId] ?? null,
    domain_tags: domains,
    overall_readiness: readiness,
    readiness_score: readiness,
    bucket,
    skills: skillDimension(matched, missing, gaps, readiness),
    certifications: certificationDimension(certifications),
    seniority: {
      user_seniority: "Senior Backend Engineer",
      role_seniority: jobTitle,
      fit: seniorityGap === "match" ? "aligned" : "stretch",
      user_level: "senior",
      role_level: seniorityGap === "under" ? "manager" : "senior",
      user_years: 7,
      gap: seniorityGap,
      note:
        seniorityGap === "under"
          ? "This role needs people-management proof beyond the current technical lead signal."
          : "Current seniority is aligned; focus on role-specific proof.",
      summary:
        seniorityGap === "under"
          ? "Technically senior, with leadership evidence still developing."
          : "Seniority signal is aligned with this role.",
    },
    grounding_used: missing.slice(0, 3),
    action_plan: gaps.slice(0, 3).map((gap) => ({
      title: `Build proof for ${gap.required_skill}`,
      description: gap.suggestion,
      effort: gap.transferability >= 0.5 ? "low" : "medium",
      priority: gap.severity,
    })),
    narrative: {
      readiness_summary:
        readiness >= 0.75
          ? `${jobTitle} is a strong near-term option because the profile already shows several core role signals.`
          : `${jobTitle} is reachable, but the profile needs more direct evidence for the highest-priority gaps.`,
      why_this_role: `${jobTitle} aligns with the profile's backend ownership, service reliability, and platform tooling evidence.`,
      main_gaps: missing.length
        ? `The main visible gaps are ${missing.slice(0, 3).join(", ")}.`
        : "No major skill gaps are visible from the supplied role requirements.",
      next_steps:
        "Start with the gap that has the closest existing evidence, then add one direct project or work artifact for the hardest gap.",
    },
  };
}

function skillDimension(
  matched: string[],
  missing: string[],
  gaps: SkillGap[],
  readiness: number,
): SkillDimension {
  return {
    matched_skills: matched,
    missing_skills: missing,
    optional_missing_skills: missing.slice(2),
    skill_gaps: gaps,
    coverage: readiness,
    status: statusFor(readiness),
    summary: `${matched.length} strong signals and ${missing.length} targeted gaps.`,
  };
}

function certificationDimension(certifications: CertificationGap[]): CertificationDimension {
  return {
    matched_certifications: ["AWS Certified Developer - Associate"],
    missing_certifications: certifications,
    held: ["AWS Certified Developer - Associate", "Professional Scrum Master I"],
    related: certifications,
    missing: certifications,
    coverage: certifications.length === 0 ? 1 : 0.55,
    status: certifications.length === 0 ? "strong" : "partial",
    summary:
      certifications.length === 0
        ? "Current certifications cover the visible role requirements."
        : "One adjacent certification would make the credential signal easier to verify.",
  };
}

function pathReport(
  roleId: keyof typeof DEMO_GAP_REPORTS,
  estimatedTimeline: string,
  milestones: CareerPathMilestone[],
  recommendedProjects: string[],
  certifications: string[],
): CareerPathReport {
  const gap = DEMO_GAP_REPORTS[roleId];
  const topGaps = gap.skills.skill_gaps.map((item) => item.required_skill).slice(0, 3);
  const milestoneText = milestones
    .slice(0, 2)
    .map((item) => item.title)
    .join(" and ");
  const certificationText = certifications.length
    ? ` Certification work stays focused on ${certifications.slice(0, 2).join(", ")}.`
    : " Projects and work artifacts carry the proof without extra credentials.";
  return {
    role_id: roleId,
    plan_summary: `${gap.job_title} is reachable by turning ${topGaps.join(
      ", ",
    )} into direct evidence. The roadmap starts with ${milestoneText} and then builds the remaining proof around the role gaps.${certificationText}`,
    current_profile_summary: `${DEMO_IDENTITY.archetype}: ${DEMO_IDENTITY.lead}`,
    target_role: gap.job_title,
    readiness_score: gap.readiness_score,
    top_gaps: topGaps,
    milestones,
    recommended_projects: recommendedProjects,
    skills_to_learn: topGaps,
    certifications,
    estimated_timeline: estimatedTimeline,
    requirement_breakdown: gap,
  };
}

function milestone(
  order: number,
  kind: CareerPathMilestone["kind"],
  title: string,
  timeline: string,
  skills: string[],
): CareerPathMilestone {
  return {
    order,
    kind,
    title,
    timeline,
    rationale: `Creates direct evidence for ${skills.join(", ")}.`,
    skills,
    projects: [],
  };
}

function statusFor(readiness: number): DimensionStatus {
  if (readiness >= 0.75) return "strong";
  if (readiness >= 0.5) return "partial";
  return "weak";
}
