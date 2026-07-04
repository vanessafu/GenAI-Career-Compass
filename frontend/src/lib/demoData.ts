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
  archetype: "Workflow Automation Software Engineer",
  lead: "Software engineer with practical experience turning repetitive product, support, and QA workflows into dependable internal tools. Current work shows a mid-level profile: shipping Python and TypeScript services, improving test coverage, coordinating release checks, and using CI feedback to reduce manual handoffs. The broader direction points toward release automation, QA engineering, and developer tooling roles where delivery habits matter as much as code.",
};

export const DEMO_CV_DATA: CVData = {
  source: {
    filename: "demo-workflow-automation-cv.pdf",
    extracted_text: null,
  },
  metadata: {
    parsing_confidence: 0.96,
    detected_language: "en",
  },
  personal_info: {
    full_name: "Alex Rivera",
    email: "alex.rivera@example.com",
    phone: null,
    location: "Remote EU",
    current_role: "Software Engineer II",
    links: ["https://github.com/alexrivera-dev", "https://linkedin.com/in/alexriveradev"],
  },
  profile_summary: {
    summary:
      "Builds internal workflow tools, test automation, and CI checks for product teams that need calmer releases and clearer quality signals.",
    current_seniority_level: "Mid",
    years_of_experience: 5,
  },
  experience: [
    {
      role: "Software Engineer II",
      organization: "HelioOps",
      industry: "Operations software",
      start_date: "2024-02",
      end_date: null,
      duration_months: 29,
      location: "Remote",
      core_responsibilities: [
        "Built Python and TypeScript tools that cut repeated release-check work for support and QA.",
        "Added Playwright smoke tests and pipeline gates for the customer portal.",
        "Coordinated release notes, bug triage, and QA sign-off across product, support, and engineering.",
      ],
      contextual_skills: [
        "Python",
        "TypeScript",
        "FastAPI",
        "React",
        "SQL",
        "Playwright",
        "Azure Pipelines",
        "Docker",
      ],
    },
    {
      role: "Software Engineer I",
      organization: "MetricLoop",
      industry: "Analytics",
      start_date: "2022-07",
      end_date: "2024-01",
      duration_months: 19,
      location: "Remote",
      core_responsibilities: [
        "Maintained Flask services and dashboards used by operations teams to investigate customer issues.",
        "Introduced Pytest coverage for data-cleanup scripts and documented recurring failure patterns.",
      ],
      contextual_skills: ["Python", "Flask", "SQL", "Pytest", "Data visualization", "Git"],
    },
    {
      role: "Automation Developer",
      organization: "FieldDesk",
      industry: "Field service software",
      start_date: "2021-04",
      end_date: "2022-06",
      duration_months: 15,
      location: "Remote",
      core_responsibilities: [
        "Wrote Bash and browser automation scripts for customer onboarding and regression checks.",
        "Moved manual checklist steps into reusable CI jobs with clearer pass/fail reporting.",
      ],
      contextual_skills: ["Bash", "Selenium", "GitLab CI", "Cucumber", "API testing"],
    },
    {
      role: "Junior Web Developer",
      organization: "Northport Labs",
      industry: "SaaS",
      start_date: "2020-06",
      end_date: "2021-03",
      duration_months: 10,
      location: "Remote",
      core_responsibilities: [
        "Shipped small React features and internal admin screens while learning production support basics.",
      ],
      contextual_skills: ["React", "TypeScript", "Git", "SQL"],
    },
  ],
  education: [
    {
      entry_type: "degree",
      degree_type: "MSc",
      field_of_study: "Software Engineering",
      institution: "Open University",
      start_date: "2023",
      end_date: "Present",
      grade: null,
      thesis_title: "Reducing manual release risk with lightweight workflow automation",
      thesis_grade: null,
      courses: ["Software Quality", "Cloud Systems", "Human-Centered Design"],
    },
    {
      entry_type: "degree",
      degree_type: "BSc",
      field_of_study: "Information Systems",
      institution: "Westbridge University",
      start_date: "2017",
      end_date: "2020",
      grade: "2.0",
      thesis_title: null,
      thesis_grade: null,
      courses: ["Databases", "Web Applications", "Statistics"],
    },
  ],
  projects: [
    {
      title: "Release Review Assistant",
      description:
        "Internal tool that combines failed jobs, open bugs, smoke-test results, and support tags into a release readiness view.",
      organization: "HelioOps",
      role: "Engineer",
      technologies: ["Python", "TypeScript", "SQL", "Azure Pipelines"],
      outcomes: ["Reduced manual release checklist work", "Made repeated blockers visible"],
      links: [],
      start_date: "2025",
      end_date: null,
    },
    {
      title: "Customer Portal Smoke Tests",
      description:
        "Playwright test pack covering login, account setup, billing changes, and support handoff paths.",
      organization: "HelioOps",
      role: "Engineer",
      technologies: ["Playwright", "TypeScript", "Docker"],
      outcomes: ["Caught regressions earlier", "Gave QA a repeatable pre-release signal"],
      links: [],
      start_date: "2024",
      end_date: null,
    },
  ],
  certifications: [],
  thesis: [
    {
      title: "Reducing manual release risk with lightweight workflow automation",
      degree_type: "MSc",
      institution: "Open University",
      supervisor: null,
      description:
        "Explores how small automation layers, quality signals, and release checklists can reduce avoidable manual coordination.",
      technologies: ["Python", "CI", "SQL"],
      grade: null,
    },
  ],
  skills_extracted: {
    technical_skills: [
      { name: "Python", proficiency_indication: "advanced" },
      { name: "TypeScript", proficiency_indication: "intermediate" },
      { name: "SQL", proficiency_indication: "advanced" },
      { name: "Bash", proficiency_indication: "intermediate" },
      { name: "Playwright", proficiency_indication: "intermediate" },
      { name: "Pytest", proficiency_indication: "intermediate" },
      { name: "Flask", proficiency_indication: "intermediate" },
      { name: "React", proficiency_indication: "intermediate" },
      { name: "Git", proficiency_indication: "advanced" },
      { name: "GitLab CI", proficiency_indication: "intermediate" },
      { name: "Azure Pipelines", proficiency_indication: "intermediate" },
      { name: "Docker", proficiency_indication: "intermediate" },
      { name: "API testing", proficiency_indication: "intermediate" },
      { name: "Cucumber", proficiency_indication: "beginner" },
      { name: "Data visualization", proficiency_indication: "intermediate" },
    ],
    inferred_skills: [],
    soft_skills: [
      { name: "Release coordination", confidence: 85 },
      { name: "QA collaboration", confidence: 80 },
      { name: "Support empathy", confidence: 75 },
    ],
    languages: [
      { language: "English", level: "C1" },
      { language: "Spanish", level: "B2" },
    ],
  },
  interests: [
    "workflow automation",
    "release quality",
    "test automation",
    "developer tooling",
    "service reliability",
  ],
  potential_direction: null,
  unmapped_information: [
    {
      label: "target_constraint",
      value: "Prefers hands-on engineering roles with visible impact on release quality.",
      source_section: "profile",
      reason_not_mapped: "Target preference used for role intent.",
    },
    {
      label: "target_constraint",
      value:
        "Wants to stay close to product teams rather than move into pure infrastructure ownership.",
      source_section: "profile",
      reason_not_mapped: "Career preference used for presentation only.",
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
  potential_direction: "",
};

export const DEMO_ROLE_MATCHES = [
  role(
    "demo-release-automation-engineer",
    "ready_now",
    "Release Automation Engineer",
    91,
    "Builds checks, scripts, and workflow tooling that make releases predictable and reduce manual handoffs between engineering and QA.",
    ["Python", "Azure Pipelines", "Git", "API testing"],
    ["release governance", "pipeline observability"],
    ["automation_scripting", "devops", "qa_testing"],
    "EUR 67k",
  ),
  role(
    "demo-qa-automation-engineer",
    "ready_now",
    "QA Automation Engineer",
    88,
    "Designs automated tests and quality signals that help teams catch regressions early and ship with clearer confidence.",
    ["Playwright", "Pytest", "API testing", "Cucumber"],
    ["test strategy", "coverage reporting"],
    ["qa_testing", "automation_scripting"],
    "EUR 65k",
  ),
  role(
    "demo-internal-tools-engineer",
    "ready_now",
    "Internal Tools Engineer",
    84,
    "Creates focused tools and dashboards that turn operational pain points into repeatable workflows for product and support teams.",
    ["TypeScript", "Python", "SQL", "React"],
    ["workflow metrics", "user research"],
    ["software_engineering", "automation_scripting", "ux_ui"],
    "EUR 68k",
  ),
  role(
    "demo-test-platform-engineer",
    "next_step",
    "Test Platform Engineer",
    76,
    "Owns shared test infrastructure, fixtures, and CI feedback loops so product teams can run reliable checks at scale.",
    ["Pytest", "Playwright", "Docker", "GitLab CI"],
    ["test infrastructure design", "parallel test execution"],
    ["qa_testing", "devops", "software_engineering"],
    "EUR 72k",
  ),
  role(
    "demo-ci-pipeline-engineer",
    "next_step",
    "CI Pipeline Engineer",
    70,
    "Maintains build and deployment pipelines, improving speed, traceability, and failure recovery across engineering teams.",
    ["Azure Pipelines", "GitLab CI", "Bash", "Docker"],
    ["pipeline architecture", "artifact management"],
    ["devops", "automation_scripting"],
    "EUR 69k",
  ),
  role(
    "demo-developer-experience-engineer",
    "next_step",
    "Developer Experience Engineer",
    66,
    "Improves everyday engineering workflows through templates, docs, automation, and tooling that remove repeated friction.",
    ["TypeScript", "Git", "Docker", "API testing"],
    ["developer portals", "tooling telemetry"],
    ["developer_experience", "platform_engineering", "software_engineering"],
    "EUR 74k",
  ),
  role(
    "demo-site-reliability-engineer",
    "aspirational",
    "Site Reliability Engineer",
    55,
    "Uses monitoring, incident practice, and automation to keep services dependable as traffic and release pace grow.",
    ["Docker", "SQL", "Bash"],
    ["SLO design", "observability", "incident response"],
    ["devops", "software_engineering"],
    "EUR 78k",
  ),
  role(
    "demo-cloud-automation-engineer",
    "aspirational",
    "Cloud Automation Engineer",
    46,
    "Automates cloud environments, deployment controls, and infrastructure workflows for teams that need repeatable operations.",
    ["Azure Pipelines", "Docker", "Bash"],
    ["infrastructure as code", "cloud networking", "secrets management"],
    ["cloud", "devops", "automation_scripting"],
    "EUR 76k",
  ),
  role(
    "demo-security-automation-engineer",
    "aspirational",
    "Security Automation Engineer",
    38,
    "Adds automated checks and secure workflow defaults so teams catch risky changes before they reach production.",
    ["API testing", "Python", "Git"],
    ["SAST tooling", "threat modeling", "secure SDLC"],
    ["cybersecurity", "automation_scripting", "software_engineering"],
    "EUR 73k",
  ),
] satisfies RoleMatch[];

export const DEMO_SELECTED_ROLE_IDS = [
  "demo-release-automation-engineer",
  "demo-test-platform-engineer",
  "demo-cloud-automation-engineer",
];

const roleDescriptions = Object.fromEntries(
  DEMO_ROLE_MATCHES.map((match) => [String(match.role_id), match.description]),
);

export const DEMO_GAP_REPORTS = {
  "demo-release-automation-engineer": gapReport({
    roleId: "demo-release-automation-engineer",
    jobTitle: "Release Automation Engineer",
    bucket: "ready_now",
    readiness: 0.72,
    domains: ["automation_scripting", "devops", "qa_testing"],
    matched: ["Python", "Azure Pipelines", "Git", "API testing"],
    gaps: [
      skillGap("release governance", "release coordination", 0.6, "medium"),
      skillGap("pipeline observability", "CI feedback work", 0.48, "medium"),
      skillGap("cross-team quality criteria", "QA sign-off coordination", 0.55, "low"),
    ],
    certifications: [],
  }),
  "demo-qa-automation-engineer": gapReport({
    roleId: "demo-qa-automation-engineer",
    jobTitle: "QA Automation Engineer",
    bucket: "ready_now",
    readiness: 0.7,
    domains: ["qa_testing", "automation_scripting"],
    matched: ["Playwright", "Pytest", "API testing", "Cucumber"],
    gaps: [
      skillGap("test strategy", "smoke-test ownership", 0.58, "medium"),
      skillGap("coverage reporting", "Pytest coverage work", 0.62, "low"),
      skillGap("exploratory testing practice", "QA collaboration", 0.42, "medium"),
    ],
    certifications: [],
  }),
  "demo-internal-tools-engineer": gapReport({
    roleId: "demo-internal-tools-engineer",
    jobTitle: "Internal Tools Engineer",
    bucket: "ready_now",
    readiness: 0.68,
    domains: ["software_engineering", "automation_scripting", "ux_ui"],
    matched: ["TypeScript", "Python", "SQL", "React"],
    gaps: [
      skillGap("workflow metrics", "release readiness views", 0.52, "medium"),
      skillGap("user research", "support empathy", 0.44, "medium"),
      skillGap("tool adoption planning", "cross-team coordination", 0.46, "low"),
    ],
    certifications: [],
  }),
  "demo-test-platform-engineer": gapReport({
    roleId: "demo-test-platform-engineer",
    jobTitle: "Test Platform Engineer",
    bucket: "next_step",
    readiness: 0.58,
    domains: ["qa_testing", "devops", "software_engineering"],
    matched: ["Pytest", "Playwright", "Docker", "GitLab CI"],
    gaps: [
      skillGap("test infrastructure design", "automated smoke tests", 0.5, "high"),
      skillGap("parallel test execution", null, 0.12, "high"),
      skillGap("fixture and test data management", "customer portal test pack", 0.4, "medium"),
    ],
    certifications: [],
  }),
  "demo-ci-pipeline-engineer": gapReport({
    roleId: "demo-ci-pipeline-engineer",
    jobTitle: "CI Pipeline Engineer",
    bucket: "next_step",
    readiness: 0.52,
    domains: ["devops", "automation_scripting"],
    matched: ["Azure Pipelines", "GitLab CI", "Bash", "Docker"],
    gaps: [
      skillGap("pipeline architecture", "reusable CI jobs", 0.46, "high"),
      skillGap("artifact management", null, 0.14, "medium"),
      skillGap("failure recovery patterns", "failed-job analysis", 0.5, "medium"),
    ],
    certifications: [certGap("Azure DevOps Engineer Expert", "Microsoft")],
  }),
  "demo-developer-experience-engineer": gapReport({
    roleId: "demo-developer-experience-engineer",
    jobTitle: "Developer Experience Engineer",
    bucket: "next_step",
    readiness: 0.47,
    domains: ["developer_experience", "platform_engineering", "software_engineering"],
    matched: ["TypeScript", "Git", "Docker", "API testing"],
    gaps: [
      skillGap("developer portals", "internal workflow tools", 0.38, "high"),
      skillGap("tooling telemetry", "release readiness metrics", 0.42, "medium"),
      skillGap("technical documentation systems", null, 0.16, "medium"),
    ],
    certifications: [],
  }),
  "demo-site-reliability-engineer": gapReport({
    roleId: "demo-site-reliability-engineer",
    jobTitle: "Site Reliability Engineer",
    bucket: "aspirational",
    readiness: 0.39,
    domains: ["devops", "software_engineering"],
    matched: ["Docker", "SQL", "Bash"],
    gaps: [
      skillGap("SLO design", "release readiness metrics", 0.32, "high"),
      skillGap("observability", null, 0.16, "high"),
      skillGap("incident response", "bug triage coordination", 0.34, "medium"),
    ],
    certifications: [],
  }),
  "demo-cloud-automation-engineer": gapReport({
    roleId: "demo-cloud-automation-engineer",
    jobTitle: "Cloud Automation Engineer",
    bucket: "aspirational",
    readiness: 0.33,
    domains: ["cloud", "devops", "automation_scripting"],
    matched: ["Azure Pipelines", "Docker", "Bash"],
    gaps: [
      skillGap("infrastructure as code", null, 0.08, "high"),
      skillGap("cloud networking", null, 0.1, "high"),
      skillGap("secrets management", "pipeline gate work", 0.28, "medium"),
    ],
    certifications: [certGap("Terraform Associate", "HashiCorp")],
  }),
  "demo-security-automation-engineer": gapReport({
    roleId: "demo-security-automation-engineer",
    jobTitle: "Security Automation Engineer",
    bucket: "aspirational",
    readiness: 0.28,
    domains: ["cybersecurity", "automation_scripting", "software_engineering"],
    matched: ["API testing", "Python", "Git"],
    gaps: [
      skillGap("SAST tooling", null, 0.08, "high"),
      skillGap("threat modeling", null, 0.1, "high"),
      skillGap("secure SDLC", "release checklist work", 0.24, "medium"),
    ],
    certifications: [certGap("CSSLP", "ISC2")],
  }),
} satisfies Record<string, GapReport>;

export const DEMO_CAREER_PATH_REPORTS = {
  "demo-release-automation-engineer": pathReport(
    "demo-release-automation-engineer",
    "5 months",
    [
      milestone(
        1,
        "skill",
        "Define release quality gates",
        "3 weeks",
        ["release governance"],
        "This turns existing release coordination into a clearer engineering signal: what must pass, who owns each check, and which exceptions are acceptable before a release moves forward.",
      ),
      milestone(
        2,
        "skill",
        "Instrument pipeline failure patterns",
        "4 weeks",
        ["pipeline observability"],
        "Although CI feedback is already present, this step makes the signal more role-specific by tracking failed-job categories, flaky checks, repeated blockers, and time-to-recovery.",
      ),
      milestone(
        3,
        "project",
        "Build a release readiness dashboard",
        "4 weeks",
        ["workflow automation", "quality signals"],
        "A focused dashboard can show practical ability to combine test results, open bugs, failed jobs, and support risk into one view that release owners can trust.",
      ),
      milestone(
        4,
        "experience",
        "Run one release review with QA and support",
        "4 weeks",
        ["cross-team quality criteria"],
        "This creates evidence that the automation is not only technical, but useful in the human workflow where engineering, QA, support, and product decide whether a release is ready.",
      ),
      milestone(
        5,
        "certification",
        "Complete a focused DevOps workflow course",
        "4 weeks",
        ["CI/CD practice"],
        "A small credential or course is enough here; the main value is giving structure to pipeline design vocabulary while the project work carries most of the proof.",
      ),
    ],
    [
      "Build a release readiness dashboard that combines CI failures, smoke tests, open bugs, and support tags.",
    ],
    [],
    "You're already close to this role: Python automation, CI checks, QA collaboration, and release coordination all line up well. The main upgrade is to turn those pieces into explicit release governance and observable pipeline evidence.",
  ),
  "demo-qa-automation-engineer": pathReport(
    "demo-qa-automation-engineer",
    "4 months",
    [
      milestone(
        1,
        "skill",
        "Write a test strategy for one product area",
        "3 weeks",
        ["test strategy"],
        "The current profile already shows test implementation; this step adds the missing planning layer by explaining which risks are covered by unit, API, browser, and exploratory checks.",
      ),
      milestone(
        2,
        "project",
        "Expand the smoke-test pack into regression coverage",
        "4 weeks",
        ["Playwright", "regression testing"],
        "This deepens the existing browser automation evidence and shows that the tests can protect important workflows beyond a small pre-release smoke suite.",
      ),
      milestone(
        3,
        "skill",
        "Add coverage and flake reporting",
        "4 weeks",
        ["coverage reporting"],
        "QA automation roles need trustworthy signals, not just more tests. Reporting makes it clear which checks are stable, which areas are thin, and where maintenance is needed.",
      ),
      milestone(
        4,
        "experience",
        "Pair with QA on exploratory charters",
        "3 weeks",
        ["exploratory testing practice"],
        "This connects automation work to real tester judgment and helps avoid the common gap where automated checks exist but do not reflect the highest-risk user journeys.",
      ),
    ],
    ["Turn the customer portal smoke tests into a documented regression pack with coverage notes."],
    [],
    "QA Automation Engineer is a realistic near-term move because the demo profile already includes Playwright, Pytest, API testing, and QA handoff work. The roadmap mainly adds strategy, reporting, and tester collaboration depth.",
  ),
  "demo-internal-tools-engineer": pathReport(
    "demo-internal-tools-engineer",
    "4 months",
    [
      milestone(
        1,
        "skill",
        "Map one support workflow end to end",
        "3 weeks",
        ["user research", "workflow mapping"],
        "The profile has support empathy, but this step makes it concrete by showing the current actors, handoffs, wait states, and repeated decisions inside one messy operational workflow.",
      ),
      milestone(
        2,
        "project",
        "Add usage metrics to an internal tool",
        "3 weeks",
        ["workflow metrics"],
        "Internal tools roles benefit from adoption proof. Lightweight metrics show whether the tool actually reduces manual work or simply shifts effort to another part of the process.",
      ),
      milestone(
        3,
        "experience",
        "Run a feedback cycle with support users",
        "4 weeks",
        ["tool adoption planning"],
        "This creates evidence that the tool was shaped by the people using it, not only by engineering assumptions about what should be automated.",
      ),
      milestone(
        4,
        "project",
        "Publish a before-and-after workflow case study",
        "3 weeks",
        ["communication", "impact measurement"],
        "A short case study makes the role fit visible by tying code changes to saved steps, fewer handoffs, and clearer ownership.",
      ),
    ],
    ["Measure adoption and saved manual steps for one internal release or support workflow."],
    [],
    "Internal Tools Engineer fits the product-facing side of this demo profile. The strongest proof will come from showing not just that a tool was built, but that it changed a real workflow.",
  ),
  "demo-test-platform-engineer": pathReport(
    "demo-test-platform-engineer",
    "5 months",
    [
      milestone(
        1,
        "role",
        "Reframe current automation as shared test platform work",
        "2 weeks",
        ["test infrastructure design"],
        "Start by translating existing smoke tests, fixtures, and CI checks into platform language: shared ownership, reusable patterns, reliability of the test environment, and team adoption.",
      ),
      milestone(
        2,
        "skill",
        "Design a reusable test fixture layer",
        "4 weeks",
        ["fixture and test data management"],
        "The current tests prove workflow coverage, but platform roles need reusable foundations. A fixture layer shows other engineers can create reliable scenarios without rebuilding setup code.",
      ),
      milestone(
        3,
        "skill",
        "Run tests in parallel with stable reporting",
        "4 weeks",
        ["parallel test execution"],
        "Parallel execution is a visible gap. This step demonstrates the ability to speed up feedback while controlling flakiness, isolation problems, and reporting noise.",
      ),
      milestone(
        4,
        "project",
        "Create a test environment health page",
        "4 weeks",
        ["test infrastructure"],
        "A health page makes hidden platform issues visible: environment status, fixture freshness, flaky suites, and the checks that block reliable CI feedback.",
      ),
      milestone(
        5,
        "experience",
        "Onboard one team to the shared test setup",
        "3 weeks",
        ["developer enablement"],
        "This proves the work is usable outside the original owner and addresses the collaboration side of test platform roles.",
      ),
    ],
    [
      "Build a reusable Playwright/Pytest fixture layer with parallel CI reporting and a test environment health page.",
    ],
    [],
    "This is a next-step role: the demo profile has strong test automation ingredients, but needs more shared-infrastructure proof before it reads like test platform ownership.",
  ),
  "demo-ci-pipeline-engineer": pathReport(
    "demo-ci-pipeline-engineer",
    "4 months",
    [
      milestone(
        1,
        "skill",
        "Diagram the current CI workflow",
        "3 weeks",
        ["pipeline architecture"],
        "This turns hands-on CI job experience into architecture evidence by showing triggers, dependencies, failure points, artifact flow, and ownership boundaries.",
      ),
      milestone(
        2,
        "project",
        "Standardize build artifacts for one service",
        "4 weeks",
        ["artifact management"],
        "Artifact handling is not visible yet. A small standardization project shows that builds can be reproduced, traced, and promoted without relying on ad hoc release steps.",
      ),
      milestone(
        3,
        "skill",
        "Add retry and failure recovery patterns",
        "4 weeks",
        ["failure recovery patterns"],
        "CI pipeline roles need more than green builds. This step shows practical handling of flaky jobs, transient failures, and clear escalation when automation cannot safely recover.",
      ),
      milestone(
        4,
        "certification",
        "Prepare Azure DevOps Engineer fundamentals",
        "4 weeks",
        ["CI/CD practice"],
        "Certification prep is useful here because it fills vocabulary around pipeline design, environments, approvals, and artifacts while the project work proves applied ability.",
      ),
    ],
    [
      "Redesign one service's CI flow with artifact tracking, retry rules, and clearer failure reporting.",
    ],
    ["Azure DevOps Engineer Expert"],
    "CI Pipeline Engineer is adjacent to the current work, but less ready than release automation because the profile needs stronger architecture and artifact-management evidence.",
  ),
  "demo-developer-experience-engineer": pathReport(
    "demo-developer-experience-engineer",
    "4 months",
    [
      milestone(
        1,
        "skill",
        "Interview engineers about repeated workflow friction",
        "4 weeks",
        ["developer research"],
        "Developer experience work starts with understanding where engineers lose time. This step prevents the demo from reading like generic tooling without a real workflow problem.",
      ),
      milestone(
        2,
        "project",
        "Create a service starter template",
        "4 weeks",
        ["developer portals", "templates"],
        "A starter template connects existing automation skills to a developer-facing artifact that reduces repeated setup work and makes best practices easier to follow.",
      ),
      milestone(
        3,
        "skill",
        "Measure template adoption and failed setup steps",
        "4 weeks",
        ["tooling telemetry"],
        "Telemetry turns a helpful tool into a role-ready signal by showing where teams adopt it, where they still get stuck, and whether support requests go down.",
      ),
      milestone(
        4,
        "experience",
        "Write onboarding docs for one workflow",
        "4 weeks",
        ["technical documentation systems"],
        "Clear documentation is part of the product surface for internal tooling. This step shows the ability to make automation understandable to teammates.",
      ),
    ],
    ["Build and measure a service starter template for one common backend workflow."],
    [],
    "Developer Experience Engineer is a plausible stretch because the profile already shows internal tooling and cross-team support, but it needs more direct evidence of adoption and documentation.",
  ),
  "demo-site-reliability-engineer": pathReport(
    "demo-site-reliability-engineer",
    "5 months",
    [
      milestone(
        1,
        "skill",
        "Define SLOs for one customer workflow",
        "4 weeks",
        ["SLO design"],
        "The current profile has release quality signals, but SRE work needs service health targets. Start with one workflow and define latency, error, and availability expectations.",
      ),
      milestone(
        2,
        "project",
        "Add basic observability to the workflow",
        "4 weeks",
        ["observability"],
        "Observability is not yet visible enough. Instrumenting logs, metrics, and alerts around one important workflow creates a concrete bridge from QA signals to service reliability.",
      ),
      milestone(
        3,
        "experience",
        "Participate in an incident review",
        "4 weeks",
        ["incident response"],
        "Incident participation adds the operational judgment that is missing from a mostly automation-focused background.",
      ),
      milestone(
        4,
        "project",
        "Link release checks to service health indicators",
        "4 weeks",
        ["release reliability"],
        "This connects the candidate's strongest release-quality evidence to SRE-style outcomes by showing whether release gates predict healthier production behavior.",
      ),
      milestone(
        5,
        "skill",
        "Practice error budget tradeoff decisions",
        "4 weeks",
        ["reliability planning"],
        "This adds decision-making depth: when to slow delivery, when to accept risk, and how to communicate reliability tradeoffs to product teams.",
      ),
    ],
    ["Instrument one customer workflow and connect its SLOs to release readiness checks."],
    [],
    "SRE is aspirational for this demo profile. The automation habits help, but the roadmap needs to add observability, incidents, and reliability decision-making before the role is credible.",
  ),
  "demo-cloud-automation-engineer": pathReport(
    "demo-cloud-automation-engineer",
    "5 months",
    [
      milestone(
        1,
        "skill",
        "Build core infrastructure as code knowledge",
        "3 weeks",
        ["infrastructure as code"],
        "Infrastructure as code is the biggest visible gap, so the first step should establish the basics: modules, state, variables, review flow, and safe environment changes.",
      ),
      milestone(
        2,
        "skill",
        "Strengthen cloud networking fundamentals",
        "4 weeks",
        ["cloud networking"],
        "Cloud automation work depends on understanding how services actually connect. This step covers subnets, routing, private access, firewalls, and environment boundaries.",
      ),
      milestone(
        3,
        "skill",
        "Add secrets handling to a pipeline",
        "4 weeks",
        ["secrets management"],
        "The profile has pipeline gates, but cloud roles require safer handling of credentials, environment variables, and deployment permissions.",
      ),
      milestone(
        4,
        "project",
        "Provision a small review environment",
        "4 weeks",
        ["cloud automation"],
        "A practical project makes the learning concrete by provisioning a temporary environment from code, running checks, and tearing it down cleanly.",
      ),
      milestone(
        5,
        "certification",
        "Prepare Terraform Associate fundamentals",
        "4 weeks",
        ["infrastructure as code"],
        "This certification directly supports the identified infrastructure-as-code gap and gives structure to the concepts used in the review-environment project.",
      ),
    ],
    [
      "Provision an ephemeral review environment from code with secrets handling and teardown automation.",
    ],
    ["Terraform Associate"],
    "Cloud Automation Engineer is intentionally a stretch. The demo profile has scripting and CI foundations, but needs direct infrastructure, networking, and secrets-management proof.",
  ),
  "demo-security-automation-engineer": pathReport(
    "demo-security-automation-engineer",
    "5 months",
    [
      milestone(
        1,
        "skill",
        "Learn secure SDLC checkpoints",
        "3 weeks",
        ["secure SDLC"],
        "The profile has release checklist experience, so start by adding security-specific gates: dependency review, code scanning, risk acceptance, and release-blocking criteria.",
      ),
      milestone(
        2,
        "skill",
        "Add SAST to one service pipeline",
        "4 weeks",
        ["SAST tooling"],
        "Security automation needs direct scanner experience. This step shows how to add a tool, tune noisy findings, and make the output useful to developers.",
      ),
      milestone(
        3,
        "project",
        "Threat-model one internal workflow",
        "4 weeks",
        ["threat modeling"],
        "Threat modeling is not visible yet. A small model for an internal workflow gives context to the automated checks and shows security reasoning beyond tool setup.",
      ),
      milestone(
        4,
        "experience",
        "Review scanner findings with an engineer",
        "4 weeks",
        ["developer enablement"],
        "This adds the human side of security automation: helping a teammate understand and fix findings without turning the pipeline into unexplained noise.",
      ),
      milestone(
        5,
        "certification",
        "Complete secure coding fundamentals",
        "4 weeks",
        ["secure SDLC"],
        "A focused course or credential is useful here because the role is a larger stretch and needs baseline security vocabulary before deeper specialization.",
      ),
    ],
    ["Add a tuned SAST check and threat model to one internal workflow pipeline."],
    ["CSSLP"],
    "Security Automation Engineer is the furthest stretch. It keeps the automation theme, but the profile needs direct security tooling and threat-modeling evidence first.",
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
  salary: string,
  matchedCertifications: string[] = [],
): RoleMatch {
  return {
    role_id: roleId,
    bucket,
    title,
    matching_score: score,
    salary,
    description,
    esco_title: title,
    esco_uri: `demo:${roleId}`,
    matched_skills: matchedSkills,
    missing_skills: missingSkills,
    matched_domains: matchedDomains,
    matched_certifications: matchedCertifications,
  };
}

function skillGap(
  requiredSkill: string,
  closestSkill: string | null,
  transferability: number,
  severity: SkillGap["severity"],
): SkillGap {
  const bridge = closestSkill
    ? `${requiredSkill} is partly covered by ${closestSkill}. Continue building this area with a targeted artifact that shows the skill in the role context.`
    : `${requiredSkill} is not visible yet. Add one concrete work example, project, or training artifact before presenting this as a strong role signal.`;

  return {
    skill: requiredSkill,
    importance: severity,
    domain: "",
    suggestion: bridge,
    required_skill: requiredSkill,
    display: requiredSkill,
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
      "This credential would make the missing certification signal easier to verify for the role.",
    required_certification: name,
    normalized_name: name.toLowerCase(),
    user_closest_certification: null,
    similarity: 0,
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
      user_seniority: "Software Engineer II",
      role_seniority: jobTitle,
      fit: seniorityGap === "match" ? "aligned" : "stretch",
      user_level: "mid",
      role_level: seniorityGap === "under" ? "senior" : "mid",
      user_years: 5,
      gap: seniorityGap,
      note:
        seniorityGap === "under"
          ? "This role needs broader ownership proof than the current mid-level engineering signal."
          : "Seniority is broadly aligned; focus on role-specific evidence.",
      summary:
        seniorityGap === "under"
          ? "Mid-level engineering base, with senior ownership evidence still developing."
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
        readiness >= 0.65
          ? `${jobTitle} is a realistic near-term option because the existing automation, QA, and release evidence already lines up with the role.`
          : `${jobTitle} is possible, but it needs more direct proof for the biggest gaps before it reads as a confident next move.`,
      why_this_role: `${jobTitle} connects to the profile's workflow automation, quality signal, and cross-team delivery evidence.`,
      main_gaps: missing.length
        ? `The main visible gaps are ${missing.slice(0, 3).join(", ")}.`
        : "No major skill gaps are visible from the supplied role requirements.",
      next_steps:
        "Start with the gap that is closest to existing work, then build one concrete artifact that validates the harder missing skill.",
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
    summary: `${matched.length} visible strengths and ${missing.length} targeted gaps.`,
  };
}

function certificationDimension(certifications: CertificationGap[]): CertificationDimension {
  return {
    matched_certifications: [],
    missing_certifications: certifications,
    held: [],
    related: certifications,
    missing: certifications,
    coverage: certifications.length === 0 ? 1 : 0,
    status: certifications.length === 0 ? "strong" : "weak",
    summary:
      certifications.length === 0
        ? "No role-specific certification is needed for this path."
        : "A targeted certification would make the missing credential signal easier to verify.",
  };
}

function pathReport(
  roleId: keyof typeof DEMO_GAP_REPORTS,
  estimatedTimeline: string,
  milestones: CareerPathMilestone[],
  recommendedProjects: string[],
  certifications: string[],
  planSummary: string,
): CareerPathReport {
  const gap = DEMO_GAP_REPORTS[roleId];
  const topGaps = gap.skills.skill_gaps.map((item) => item.required_skill).slice(0, 3);
  return {
    role_id: roleId,
    plan_summary: planSummary,
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
  rationale: string,
): CareerPathMilestone {
  return {
    order,
    kind,
    title,
    timeline,
    rationale,
    skills,
    projects: [],
  };
}

function statusFor(readiness: number): DimensionStatus {
  if (readiness >= 0.65) return "strong";
  if (readiness >= 0.4) return "partial";
  return "weak";
}
