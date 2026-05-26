#!/usr/bin/env python3
"""Phase 3 deterministic domain tagging for Career Compass roles.

One-time database enrichment script. Kept for auditability and controlled reruns
while rebuilding the seeded Career Compass database; not app runtime code.
Prefer --dry-run before any write-mode rerun.

This script reads existing Supabase `career_roles`, scores each role against a
seed domain taxonomy, optionally discovers guarded new domain tags from repeated
role clusters, writes review/taxonomy CSVs, and updates only
`career_roles.domain_tags`.

Examples:
    python scripts/tag_career_roles.py --dry-run
    python scripts/tag_career_roles.py --only-untagged --review-output data/domain_tags_review.csv
    python scripts/tag_career_roles.py --force
    python scripts/tag_career_roles.py --dry-run --no-discover-new-tags
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence


TITLE_WEIGHT = 5
SKILL_WEIGHT = 3
DESCRIPTION_WEIGHT = 1
CERTIFICATION_WEIGHT = 1
MIN_ASSIGN_SCORE = 3
MAX_TAGS_PER_ROLE = 3
AUTO_ADD_MIN_ROLES = 3
BATCH_SIZE = 1000
AUTO_ADD_SINGLE_ROLE_TAGS = frozenset(
    {
        "ar_vr",
        "business_analysis",
        "gis_geospatial",
        "robotics",
        "sales_engineering",
    }
)


@dataclass(frozen=True)
class SchemaConfig:
    roles_table: str = "career_roles"
    role_skills_table: str = "role_skills"
    role_certifications_table: str = "role_certifications"
    role_id_column: str = "role_id"
    job_title_column: str = "job_title"
    job_description_column: str = "job_description"
    raw_skills_column: str = "raw_skills"
    raw_certifications_column: str = "raw_certifications"
    source_row_hash_column: str = "source_row_hash"
    domain_tags_column: str = "domain_tags"
    skill_name_column: str = "skill_name"
    certification_name_column: str = "certification_name"
    normalized_certification_name_column: str = "normalized_certification_name"


DEFAULT_SCHEMA = SchemaConfig()


@dataclass
class RoleRecord:
    role_id: Any
    job_title: str
    job_description: str = ""
    raw_skills: str = ""
    raw_certifications: str = ""
    source_row_hash: str | None = None
    domain_tags: str | None = None
    role_skills: list[str] = field(default_factory=list)
    role_certifications: list[str] = field(default_factory=list)


@dataclass
class TagDefinition:
    slug: str
    label: str
    keywords: tuple[str, ...]
    source: str
    status: str
    reason: str
    order: int
    matched_role_count: int = 0
    example_role_titles: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ManualOverride:
    domain_tags: list[str]
    notes: str = ""


@dataclass
class ManualOverrides:
    by_role_id: dict[str, ManualOverride] = field(default_factory=dict)
    by_job_title: dict[str, ManualOverride] = field(default_factory=dict)

    def find_for(self, role: RoleRecord) -> ManualOverride | None:
        role_id_key = str(role.role_id).strip()
        if role_id_key in self.by_role_id:
            return self.by_role_id[role_id_key]
        return self.by_job_title.get(role.job_title.strip())


@dataclass
class ClassificationResult:
    role: RoleRecord
    assigned_tags: list[str]
    confidence: str
    tag_scores: dict[str, int]
    matched_keywords: dict[str, list[str]]
    reason: str
    new_tags_used: list[str]
    needs_human_review: bool
    used_override: bool = False


@dataclass
class UpdateStats:
    roles_seen: int = 0
    roles_updated: int = 0
    roles_would_update: int = 0
    roles_unchanged: int = 0
    roles_skipped_existing: int = 0
    roles_without_tags: int = 0


class SupabaseError(RuntimeError):
    """Raised when Supabase returns an error response."""


SEED_TAGS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "software_engineering",
        "Software Engineering",
        (
            "software engineer",
            "software developer",
            "application developer",
            "developer",
            "programmer",
            "software development",
            "coding",
            "mainframe",
            "mainframe developer",
            "cobol",
        ),
    ),
    (
        "frontend",
        "Frontend",
        (
            "frontend",
            "front-end",
            "react",
            "angular",
            "vue",
            "html",
            "css",
            "javascript",
            "typescript",
            "ui developer",
            "web developer",
            "webmaster",
        ),
    ),
    (
        "backend",
        "Backend",
        (
            "backend",
            "back-end",
            "api",
            "server-side",
            "node.js",
            "express",
            "django",
            "flask",
            "spring",
            "java",
            "microservices",
            "rest api",
        ),
    ),
    (
        "fullstack",
        "Full Stack",
        (
            "fullstack",
            "full-stack",
            "full stack",
            "frontend and backend",
            "end-to-end web",
        ),
    ),
    ("mobile", "Mobile", ("mobile", "android", "ios", "kotlin", "swift", "react native", "flutter")),
    (
        "ux_ui",
        "UX/UI",
        (
            "ux",
            "ui",
            "user experience",
            "user interface",
            "figma",
            "product design",
            "interaction design",
            "usability",
        ),
    ),
    (
        "qa_testing",
        "QA Testing",
        (
            "qa",
            "quality assurance",
            "tester",
            "testing",
            "test automation",
            "selenium",
            "cypress",
            "playwright",
            "junit",
            "pytest",
        ),
    ),
    (
        "devops",
        "DevOps",
        (
            "devops",
            "ci/cd",
            "cicd",
            "pipeline",
            "jenkins",
            "github actions",
            "gitlab ci",
            "terraform",
            "ansible",
            "kubernetes",
            "docker",
            "deployment",
            "git",
            "gerrit",
            "tfs",
            "team foundation server",
            "source control",
            "version control",
        ),
    ),
    (
        "cloud",
        "Cloud",
        (
            "cloud",
            "aws",
            "azure",
            "gcp",
            "google cloud",
            "cloud platform",
            "cloud architecture",
            "cloud engineer",
            "serverless",
        ),
    ),
    (
        "cybersecurity",
        "Cybersecurity",
        (
            "security",
            "cybersecurity",
            "cyber security",
            "infosec",
            "penetration",
            "pentest",
            "vulnerability",
            "threat",
            "soc",
            "siem",
            "firewall",
            "incident response",
        ),
    ),
    (
        "data_analytics",
        "Data Analytics",
        (
            "data analyst",
            "analytics",
            "business intelligence",
            "data analysis",
            "bi",
            "tableau",
            "power bi",
            "dashboard",
            "reporting",
            "excel",
            "statistics",
        ),
    ),
    (
        "data_engineering",
        "Data Engineering",
        (
            "data engineer",
            "etl",
            "elt",
            "data pipeline",
            "spark",
            "airflow",
            "kafka",
            "data warehouse",
            "big data",
        ),
    ),
    (
        "ai_ml",
        "AI/ML",
        (
            "ai",
            "artificial intelligence",
            "machine learning",
            "ml",
            "deep learning",
            "neural",
            "nlp",
            "computer vision",
            "model training",
            "tensorflow",
            "pytorch",
        ),
    ),
    (
        "database",
        "Database",
        (
            "database",
            "sql",
            "postgresql",
            "mysql",
            "oracle",
            "mongodb",
            "nosql",
            "dba",
            "database administrator",
        ),
    ),
    (
        "infrastructure",
        "Infrastructure",
        (
            "infrastructure",
            "systems administrator",
            "system administrator",
            "linux",
            "windows server",
            "servers",
            "virtualization",
            "vmware",
            "storage",
        ),
    ),
    (
        "networking",
        "Networking",
        (
            "network",
            "networking",
            "tcp/ip",
            "dns",
            "routing",
            "switching",
            "cisco",
            "lan",
            "wan",
            "network administrator",
        ),
    ),
    (
        "support",
        "Support",
        (
            "support",
            "help desk",
            "helpdesk",
            "service desk",
            "technical support",
            "troubleshooting",
            "it support",
        ),
    ),
    (
        "automation_scripting",
        "Automation Scripting",
        (
            "automation",
            "scripting",
            "python scripts",
            "powershell",
            "bash",
            "shell",
            "robotic process automation",
            "rpa",
        ),
    ),
    (
        "architecture",
        "Architecture",
        (
            "architect",
            "architecture",
            "solution architect",
            "systems architect",
            "enterprise architect",
            "technical architect",
        ),
    ),
    (
        "product_management",
        "Product Management",
        (
            "product manager",
            "product owner",
            "roadmap",
            "product strategy",
            "requirements",
            "user stories",
        ),
    ),
    (
        "project_management",
        "Project Management",
        (
            "project manager",
            "project management",
            "scrum master",
            "agile coach",
            "delivery manager",
            "pmp",
        ),
    ),
    (
        "management",
        "Management",
        (
            "manager",
            "lead",
            "director",
            "head of",
            "team lead",
            "engineering manager",
            "it manager",
        ),
    ),
    (
        "embedded_iot",
        "Embedded IoT",
        (
            "embedded",
            "firmware",
            "iot",
            "internet of things",
            "microcontroller",
            "arduino",
            "raspberry pi",
            "sensors",
        ),
    ),
    (
        "blockchain_web3",
        "Blockchain Web3",
        (
            "blockchain",
            "web3",
            "smart contract",
            "solidity",
            "ethereum",
            "crypto",
            "decentralized",
        ),
    ),
    (
        "game_development",
        "Game Development",
        (
            "game",
            "unity",
            "unreal",
            "game developer",
            "gameplay",
            "3d graphics",
        ),
    ),
]


DISCOVERABLE_TAGS: list[tuple[str, str, tuple[str, ...], str]] = [
    (
        "erp_crm",
        "ERP/CRM",
        (
            "erp",
            "crm",
            "sap",
            "s/4hana",
            "salesforce",
            "microsoft dynamics",
            "dynamics 365",
            "enterprise resource planning",
            "customer relationship management",
            "netsuite",
        ),
        "Repeated ERP or CRM platform roles form a distinct business systems domain.",
    ),
    (
        "business_analysis",
        "Business Analysis",
        (
            "business analyst",
            "business analysis",
            "business systems analyst",
            "digital transformation",
            "process analysis",
            "requirements elicitation",
            "brd",
            "stakeholder analysis",
        ),
        "Business analysis roles focus on process and requirements work rather than one technical stack.",
    ),
    (
        "technical_writing",
        "Technical Writing",
        (
            "technical writer",
            "documentation specialist",
            "documentation",
            "api documentation",
            "developer documentation",
            "knowledge base",
            "manuals",
            "content writer",
            "docs",
        ),
        "Documentation and technical content roles are better represented as a writing domain.",
    ),
    (
        "it_governance",
        "IT Governance",
        (
            "it governance",
            "governance",
            "cobit",
            "itil",
            "policy",
            "audit controls",
            "enterprise governance",
        ),
        "Governance roles emphasize policies, controls, and operating models.",
    ),
    (
        "compliance_risk",
        "Compliance Risk",
        (
            "compliance",
            "risk",
            "grc",
            "gdpr",
            "iso 27001",
            "sox",
            "audit",
            "risk management",
        ),
        "Compliance and risk roles are distinct from hands-on cybersecurity operations.",
    ),
    (
        "digital_marketing_tech",
        "Digital Marketing Tech",
        (
            "seo",
            "sem",
            "marketing automation",
            "google analytics",
            "hubspot",
            "campaign",
            "martech",
            "digital marketing",
        ),
        "Digital marketing technology roles combine marketing systems and analytics.",
    ),
    (
        "education_training",
        "Education Training",
        (
            "trainer",
            "technical trainer",
            "software trainer",
            "instructor",
            "education",
            "training specialist",
            "learning and development",
            "instructional design",
            "elearning",
            "lms",
            "curriculum",
            "enablement",
        ),
        "Training roles are a separate career path from building or operating systems.",
    ),
    (
        "research",
        "Research",
        (
            "researcher",
            "research scientist",
            "research engineer",
            "r&d",
            "research and development",
            "scientific computing",
        ),
        "Research roles emphasize investigation and prototype work as a domain.",
    ),
    (
        "observability",
        "Observability",
        (
            "observability",
            "monitoring",
            "logging",
            "log analytics",
            "elk",
            "elasticsearch",
            "logstash",
            "kibana",
            "fluentd",
            "grafana",
            "prometheus",
            "splunk",
        ),
        "Monitoring, logging, and observability platform roles form a distinct operations domain.",
    ),
    (
        "gis_geospatial",
        "GIS Geospatial",
        (
            "gis",
            "geographic information systems",
            "geospatial",
            "spatial analysis",
            "mapping systems",
            "arcgis",
            "qgis",
        ),
        "GIS and geospatial technology roles use distinct spatial data systems and workflows.",
    ),
    (
        "ar_vr",
        "AR/VR",
        (
            "ar",
            "vr",
            "augmented reality",
            "virtual reality",
            "mixed reality",
            "xr",
            "oculus",
            "quest",
        ),
        "AR, VR, and XR roles are distinct enough to avoid forcing them into game development.",
    ),
    (
        "robotics",
        "Robotics",
        (
            "robotics",
            "robot",
            "ros",
            "autonomous systems",
            "mechatronics",
            "motion planning",
        ),
        "Robotics roles combine software, hardware, and automation in a distinct domain.",
    ),
    (
        "sales_engineering",
        "Sales Engineering",
        (
            "sales engineer",
            "pre-sales",
            "presales",
            "solutions consultant",
            "solution consultant",
            "technical sales",
        ),
        "Sales engineering roles combine technical discovery and customer-facing sales support.",
    ),
    (
        "animation_graphics",
        "Animation Graphics",
        (
            "animation",
            "animator",
            "computer graphics",
            "motion graphics",
            "vfx",
            "visual effects",
            "2d artist",
            "3d artist",
            "character designer",
            "storyboard artist",
            "rigging artist",
            "compositor",
            "layout artist",
            "forensic animator",
        ),
        "Animation, visual effects, and graphics roles are a repeated creative technology cluster.",
    ),
    (
        "healthcare_it",
        "Healthcare IT",
        (
            "healthcare",
            "health informatics",
            "ehr",
            "emr",
            "hl7",
            "fhir",
            "clinical systems",
        ),
        "Healthcare IT roles have domain-specific systems, standards, and workflows.",
    ),
    (
        "fintech",
        "Fintech",
        (
            "fintech",
            "financial technology",
            "banking",
            "payments",
            "trading",
            "payment systems",
            "financial systems",
        ),
        "Financial technology roles reflect a repeated industry-specific IT domain.",
    ),
]


def normalize_supabase_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            "SUPABASE_URL must be a full URL, such as "
            "https://your-project-ref.supabase.co"
        )

    dashboard_prefix = "/dashboard/project/"
    if parsed.netloc == "supabase.com" and parsed.path.startswith(dashboard_prefix):
        project_ref = parsed.path[len(dashboard_prefix) :].split("/", 1)[0]
        if project_ref:
            return f"https://{project_ref}.supabase.co"

    return value.strip().rstrip("/")


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or name in os.environ:
            continue

        if (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]

        os.environ[name] = value


def build_seed_taxonomy() -> dict[str, TagDefinition]:
    taxonomy: dict[str, TagDefinition] = {}
    for order, (slug, label, keywords) in enumerate(SEED_TAGS):
        taxonomy[slug] = TagDefinition(
            slug=slug,
            label=label,
            keywords=keywords,
            source="seed",
            status="seed",
            reason="Seed Phase 3 taxonomy tag.",
            order=order,
        )
    return taxonomy


def build_taxonomy(
    roles: Sequence[RoleRecord],
    discover_new_tags: bool = True,
) -> dict[str, TagDefinition]:
    taxonomy = build_seed_taxonomy()
    populate_taxonomy_evidence(taxonomy.values(), roles)

    if not discover_new_tags:
        return taxonomy

    next_order = len(taxonomy)
    for slug, label, keywords, reason in DISCOVERABLE_TAGS:
        validate_tag_slug(slug, taxonomy)
        candidate = TagDefinition(
            slug=slug,
            label=label,
            keywords=keywords,
            source="discovered",
            status="needs_review",
            reason=reason,
            order=next_order,
        )
        populate_taxonomy_evidence([candidate], roles)
        if candidate.matched_role_count < 1:
            continue
        if (
            candidate.matched_role_count >= AUTO_ADD_MIN_ROLES
            or slug in AUTO_ADD_SINGLE_ROLE_TAGS
        ):
            candidate.status = "auto_added"
            if slug in AUTO_ADD_SINGLE_ROLE_TAGS:
                candidate.reason += " Approved as a meaningful single-role domain tag."
        taxonomy[slug] = candidate
        next_order += 1

    return taxonomy


def populate_taxonomy_evidence(
    tags: Iterable[TagDefinition],
    roles: Sequence[RoleRecord],
) -> None:
    for tag in tags:
        examples: list[str] = []
        keywords_seen: set[str] = set()
        matched_count = 0

        for item in roles:
            score, matched_keywords = score_tag(item, tag)
            if score < MIN_ASSIGN_SCORE:
                continue

            matched_count += 1
            if len(examples) < 5:
                examples.append(item.job_title)
            keywords_seen.update(matched_keywords)

        tag.matched_role_count = matched_count
        tag.example_role_titles = examples
        tag.matched_keywords = sorted(keywords_seen)


def score_tag(role: RoleRecord, tag: TagDefinition) -> tuple[int, list[str]]:
    fields = [
        (role.job_title, TITLE_WEIGHT),
        (combine_skill_text(role), SKILL_WEIGHT),
        (role.job_description, DESCRIPTION_WEIGHT),
        (combine_certification_text(role), CERTIFICATION_WEIGHT),
    ]
    score = 0
    matched_keywords: list[str] = []

    for keyword in tag.keywords:
        matched_this_keyword = False
        for field_text, weight in fields:
            if keyword_matches(field_text, keyword):
                score += weight
                matched_this_keyword = True
        if matched_this_keyword:
            matched_keywords.append(keyword)

    return score, matched_keywords


def classify_role(
    role: RoleRecord,
    taxonomy: dict[str, TagDefinition],
    overrides: ManualOverrides | None = None,
) -> ClassificationResult:
    override = overrides.find_for(role) if overrides else None
    if override:
        assigned_tags = override.domain_tags[:MAX_TAGS_PER_ROLE]
        new_tags_used = [
            tag
            for tag in assigned_tags
            if taxonomy.get(tag) and taxonomy[tag].source == "manual_override"
        ]
        return ClassificationResult(
            role=role,
            assigned_tags=assigned_tags,
            confidence="high",
            tag_scores={tag: 999 for tag in assigned_tags},
            matched_keywords={tag: ["manual_override"] for tag in assigned_tags},
            reason=f"Manual override applied. {override.notes}".strip(),
            new_tags_used=new_tags_used,
            needs_human_review=False,
            used_override=True,
        )

    tag_scores: dict[str, int] = {}
    matched_keywords: dict[str, list[str]] = {}
    for slug, tag in taxonomy.items():
        if tag.status == "needs_review":
            continue
        score, matches = score_tag(role, tag)
        if score <= 0:
            continue
        tag_scores[slug] = score
        matched_keywords[slug] = matches

    ranked = sorted(
        (
            (slug, score)
            for slug, score in tag_scores.items()
            if score >= MIN_ASSIGN_SCORE
        ),
        key=lambda item: (-item[1], taxonomy[item[0]].order, item[0]),
    )
    assigned_tags = [slug for slug, _score in ranked[:MAX_TAGS_PER_ROLE]]
    used_fallback = False
    if not assigned_tags:
        fallback_tag = choose_fallback_tag(role, taxonomy)
        assigned_tags = [fallback_tag]
        ranked = [(fallback_tag, 0)]
        matched_keywords[fallback_tag] = ["fallback"]
        used_fallback = True

    confidence = "low" if used_fallback else confidence_for_scores(ranked)
    new_tags_used = [
        tag
        for tag in assigned_tags
        if taxonomy[tag].source == "discovered" and taxonomy[tag].status == "auto_added"
    ]
    needs_human_review = confidence == "low"
    reason = (
        "Fallback tag selected because no domain met the minimum deterministic score."
        if used_fallback
        else build_reason(assigned_tags, matched_keywords)
    )

    return ClassificationResult(
        role=role,
        assigned_tags=assigned_tags,
        confidence=confidence,
        tag_scores=dict(ranked[:8]),
        matched_keywords={
            tag: matched_keywords.get(tag, [])
            for tag in assigned_tags
        },
        reason=reason,
        new_tags_used=new_tags_used,
        needs_human_review=needs_human_review,
    )


def classify_roles(
    roles: Sequence[RoleRecord],
    taxonomy: dict[str, TagDefinition],
    overrides: ManualOverrides | None = None,
    only_untagged: bool = False,
) -> list[ClassificationResult]:
    selected_roles = [
        role
        for role in roles
        if not only_untagged or is_blank(role.domain_tags)
    ]
    return [
        classify_role(role, taxonomy, overrides=overrides)
        for role in selected_roles
    ]


def confidence_for_scores(ranked_scores: Sequence[tuple[str, int]]) -> str:
    if not ranked_scores:
        return "low"

    top_score = ranked_scores[0][1]
    second_score = ranked_scores[1][1] if len(ranked_scores) > 1 else 0
    tied_top_count = sum(1 for _slug, score in ranked_scores if score == top_score)

    if top_score >= 8 and tied_top_count <= 2 and second_score <= top_score:
        return "high"
    if top_score >= 5:
        return "medium"
    return "low"


def choose_fallback_tag(
    role: RoleRecord,
    taxonomy: dict[str, TagDefinition],
) -> str:
    fallback_rules = [
        (
            (
                "animation",
                "animator",
                "computer graphics",
                "motion graphics",
                "vfx",
                "visual effects",
                "2d artist",
                "3d artist",
                "character designer",
                "storyboard artist",
                "rigging artist",
                "compositor",
                "layout artist",
                "forensic animator",
            ),
            "animation_graphics",
        ),
        (("webmaster",), "frontend"),
        (
            (
                "observability",
                "monitoring",
                "logging",
                "elk",
                "fluentd",
                "grafana",
                "splunk",
            ),
            "observability",
        ),
        (("gis", "geographic information systems", "geospatial"), "gis_geospatial"),
        (("git", "gerrit", "tfs", "source control", "version control"), "devops"),
        (("digital transformation", "business consultant"), "business_analysis"),
        (("mainframe", "cobol"), "software_engineering"),
        (("developer", "programmer", "coder"), "software_engineering"),
        (("administrator", "admin", "systems"), "infrastructure"),
        (("data analysis", "analyst"), "data_analytics"),
        (("manager", "director", "lead"), "management"),
        (("consultant", "requirements", "business"), "business_analysis"),
        (("engineer",), "software_engineering"),
        (("artist", "designer"), "ux_ui"),
    ]

    for keywords, tag_slug in fallback_rules:
        if tag_is_assignable(tag_slug, taxonomy) and role_matches_any(role, keywords):
            return tag_slug

    if tag_is_assignable("software_engineering", taxonomy):
        return "software_engineering"

    for tag in sorted(taxonomy.values(), key=lambda item: item.order):
        if tag.status != "needs_review":
            return tag.slug

    raise ValueError("Cannot select a fallback tag because the taxonomy is empty.")


def tag_is_assignable(tag_slug: str, taxonomy: dict[str, TagDefinition]) -> bool:
    tag = taxonomy.get(tag_slug)
    return tag is not None and tag.status != "needs_review"


def role_matches_any(role: RoleRecord, keywords: Sequence[str]) -> bool:
    searchable_text = " ".join(
        part
        for part in [
            role.job_title,
            role.job_description,
            role.raw_skills,
            role.raw_certifications,
            " ".join(role.role_skills),
            " ".join(role.role_certifications),
        ]
        if part
    )
    return any(keyword_matches(searchable_text, keyword) for keyword in keywords)


def build_reason(
    assigned_tags: Sequence[str],
    matched_keywords: dict[str, list[str]],
) -> str:
    if not assigned_tags:
        return "No domain tag met the minimum deterministic score."

    parts = []
    for tag in assigned_tags:
        keywords = ", ".join(matched_keywords.get(tag, [])[:8])
        parts.append(f"{tag}: {keywords}" if keywords else tag)
    return "; ".join(parts)


def combine_skill_text(role: RoleRecord) -> str:
    return " ".join(
        part
        for part in [role.raw_skills, " ".join(role.role_skills)]
        if part
    )


def combine_certification_text(role: RoleRecord) -> str:
    return " ".join(
        part
        for part in [role.raw_certifications, " ".join(role.role_certifications)]
        if part
    )


def keyword_matches(text: str | None, keyword: str) -> bool:
    if not text or not keyword:
        return False

    normalized_text = text.casefold()
    normalized_keyword = keyword.casefold()
    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(normalized_keyword)
        + r"(?![a-z0-9])"
    )
    return re.search(pattern, normalized_text) is not None


def load_manual_overrides(
    path: Path,
    taxonomy: dict[str, TagDefinition],
) -> ManualOverrides:
    overrides = ManualOverrides()
    if not path.exists():
        return overrides

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return overrides
        if "domain_tags" not in reader.fieldnames:
            raise ValueError("Override CSV must include a domain_tags column.")

        for row_number, row in enumerate(reader, start=2):
            role_id = (row.get("role_id") or "").strip()
            job_title = (row.get("job_title") or "").strip()
            tags = parse_domain_tags(row.get("domain_tags") or "")
            notes = (row.get("notes") or "").strip()

            if not role_id and not job_title:
                raise ValueError(
                    f"Override row {row_number} must include role_id or job_title."
                )
            if not tags:
                raise ValueError(
                    f"Override row {row_number} must include at least one domain tag."
                )
            if len(tags) > MAX_TAGS_PER_ROLE:
                raise ValueError(
                    f"Override row {row_number} has more than {MAX_TAGS_PER_ROLE} tags."
                )

            for tag in tags:
                ensure_manual_tag(tag, taxonomy)

            override = ManualOverride(domain_tags=tags, notes=notes)
            if role_id:
                overrides.by_role_id[role_id] = override
                update_manual_taxonomy_evidence(taxonomy, tags, job_title or role_id)
            else:
                overrides.by_job_title[job_title] = override
                update_manual_taxonomy_evidence(taxonomy, tags, job_title)

    return overrides


def ensure_manual_tag(tag_slug: str, taxonomy: dict[str, TagDefinition]) -> None:
    validate_tag_slug(tag_slug, taxonomy, allow_existing=True)
    if tag_slug in taxonomy:
        return

    taxonomy[tag_slug] = TagDefinition(
        slug=tag_slug,
        label=slug_to_label(tag_slug),
        keywords=(),
        source="manual_override",
        status="manual_override",
        reason="Added from data/domain_tags_overrides.csv.",
        order=len(taxonomy),
    )


def update_manual_taxonomy_evidence(
    taxonomy: dict[str, TagDefinition],
    tags: Sequence[str],
    example_title: str,
) -> None:
    for tag_slug in tags:
        tag = taxonomy[tag_slug]
        if tag.source != "manual_override":
            continue
        tag.matched_role_count += 1
        if example_title and len(tag.example_role_titles) < 5:
            tag.example_role_titles.append(example_title)
        if "manual_override" not in tag.matched_keywords:
            tag.matched_keywords.append("manual_override")


def parse_domain_tags(value: str) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for raw_tag in value.replace(";", ",").split(","):
        tag = raw_tag.strip()
        if not tag or tag in seen:
            continue
        tags.append(tag)
        seen.add(tag)
    return tags


def validate_tag_slug(
    tag_slug: str,
    taxonomy: dict[str, TagDefinition],
    allow_existing: bool = False,
) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", tag_slug):
        raise ValueError(
            f"Invalid tag slug '{tag_slug}'. Use lowercase snake_case only."
        )

    compact_slug = tag_slug.replace("_", "")
    for existing_slug in taxonomy:
        if existing_slug == tag_slug:
            if allow_existing:
                return
            raise ValueError(f"Duplicate tag slug '{tag_slug}'.")
        if existing_slug.replace("_", "") == compact_slug:
            raise ValueError(
                f"Tag slug '{tag_slug}' is too similar to existing tag '{existing_slug}'."
            )


def slug_to_label(tag_slug: str) -> str:
    return " ".join(part.upper() if len(part) <= 3 else part.title() for part in tag_slug.split("_"))


def domain_tags_value(tags: Sequence[str]) -> str:
    return ",".join(tags)


def canonicalize_domain_tags_value(value: str | None) -> str:
    if is_blank(value):
        return ""
    return domain_tags_value(parse_domain_tags(str(value)))


def is_blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


def update_domain_tags(
    classifications: Sequence[ClassificationResult],
    client: Any,
    dry_run: bool = False,
    force: bool = False,
) -> UpdateStats:
    stats = UpdateStats(roles_seen=len(classifications))
    for result in classifications:
        next_value = domain_tags_value(result.assigned_tags)
        if not next_value:
            stats.roles_without_tags += 1
            continue

        current_value = canonicalize_domain_tags_value(result.role.domain_tags)
        if current_value == next_value:
            stats.roles_unchanged += 1
            continue
        if current_value and not force:
            stats.roles_skipped_existing += 1
            continue

        if dry_run:
            stats.roles_would_update += 1
        else:
            client.update_role_domain_tags(result.role.role_id, next_value)
            stats.roles_updated += 1

    return stats


def write_taxonomy_csv(
    taxonomy: dict[str, TagDefinition],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tag_slug",
        "tag_label",
        "source",
        "status",
        "matched_role_count",
        "example_role_titles",
        "matched_keywords",
        "reason",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for tag in sorted(taxonomy.values(), key=lambda item: item.order):
            writer.writerow(
                {
                    "tag_slug": tag.slug,
                    "tag_label": tag.label,
                    "source": tag.source,
                    "status": tag.status,
                    "matched_role_count": tag.matched_role_count,
                    "example_role_titles": "; ".join(tag.example_role_titles),
                    "matched_keywords": ", ".join(tag.matched_keywords),
                    "reason": tag.reason,
                }
            )


def write_review_csv(
    classifications: Sequence[ClassificationResult],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "role_id",
        "job_title",
        "current_domain_tags",
        "assigned_tags",
        "confidence",
        "top_tag_scores",
        "reason_or_matched_keywords",
        "new_tags_used",
        "needs_human_review",
        "used_override",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in classifications:
            writer.writerow(
                {
                    "role_id": result.role.role_id,
                    "job_title": result.role.job_title,
                    "current_domain_tags": result.role.domain_tags or "",
                    "assigned_tags": domain_tags_value(result.assigned_tags),
                    "confidence": result.confidence,
                    "top_tag_scores": format_scores(result.tag_scores),
                    "reason_or_matched_keywords": result.reason,
                    "new_tags_used": domain_tags_value(result.new_tags_used),
                    "needs_human_review": "yes" if result.needs_human_review else "no",
                    "used_override": "yes" if result.used_override else "no",
                }
            )


def format_scores(scores: dict[str, int]) -> str:
    return "; ".join(f"{tag}:{score}" for tag, score in scores.items())


class SupabaseRestClient:
    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        schema: SchemaConfig = DEFAULT_SCHEMA,
        timeout_seconds: int = 30,
    ):
        self.rest_url = normalize_supabase_url(supabase_url) + "/rest/v1"
        self.service_role_key = service_role_key
        self.schema = schema
        self.timeout_seconds = timeout_seconds

    def validate_schema(self) -> None:
        self._request(
            "GET",
            self.schema.roles_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.role_id_column,
                            self.schema.job_title_column,
                            self.schema.job_description_column,
                            self.schema.raw_skills_column,
                            self.schema.raw_certifications_column,
                            self.schema.source_row_hash_column,
                            self.schema.domain_tags_column,
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )
        self._request(
            "GET",
            self.schema.role_skills_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.role_id_column,
                            self.schema.skill_name_column,
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )
        self._request(
            "GET",
            self.schema.role_certifications_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.role_id_column,
                            self.schema.certification_name_column,
                            self.schema.normalized_certification_name_column,
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )

    def list_roles(self) -> list[RoleRecord]:
        rows = self._paged_get(
            self.schema.roles_table,
            select=",".join(
                [
                    self.schema.role_id_column,
                    self.schema.job_title_column,
                    self.schema.job_description_column,
                    self.schema.raw_skills_column,
                    self.schema.raw_certifications_column,
                    self.schema.source_row_hash_column,
                    self.schema.domain_tags_column,
                ]
            ),
            extra_query=[("order", f"{self.schema.role_id_column}.asc")],
        )
        return [
            RoleRecord(
                role_id=row.get(self.schema.role_id_column),
                job_title=row.get(self.schema.job_title_column) or "",
                job_description=row.get(self.schema.job_description_column) or "",
                raw_skills=row.get(self.schema.raw_skills_column) or "",
                raw_certifications=row.get(self.schema.raw_certifications_column) or "",
                source_row_hash=row.get(self.schema.source_row_hash_column),
                domain_tags=row.get(self.schema.domain_tags_column),
            )
            for row in rows
        ]

    def list_role_skills_by_role_id(self) -> dict[str, list[str]]:
        rows = self._paged_get(
            self.schema.role_skills_table,
            select=",".join(
                [
                    self.schema.role_id_column,
                    self.schema.skill_name_column,
                ]
            ),
            extra_query=[("order", f"{self.schema.role_id_column}.asc")],
        )
        skills_by_role_id: dict[str, list[str]] = {}
        for row in rows:
            role_id = row.get(self.schema.role_id_column)
            skill_name = row.get(self.schema.skill_name_column)
            if role_id is None or not skill_name:
                continue
            skills_by_role_id.setdefault(str(role_id), []).append(str(skill_name))
        return skills_by_role_id

    def list_role_certifications_by_role_id(self) -> dict[str, list[str]]:
        rows = self._paged_get(
            self.schema.role_certifications_table,
            select=",".join(
                [
                    self.schema.role_id_column,
                    self.schema.certification_name_column,
                    self.schema.normalized_certification_name_column,
                ]
            ),
            extra_query=[("order", f"{self.schema.role_id_column}.asc")],
        )
        certifications_by_role_id: dict[str, list[str]] = {}
        for row in rows:
            role_id = row.get(self.schema.role_id_column)
            if role_id is None:
                continue
            certification_names = [
                row.get(self.schema.certification_name_column),
                row.get(self.schema.normalized_certification_name_column),
            ]
            for certification_name in certification_names:
                if certification_name:
                    certifications_by_role_id.setdefault(str(role_id), []).append(
                        str(certification_name)
                    )
        return certifications_by_role_id

    def update_role_domain_tags(self, role_id: Any, domain_tags: str) -> None:
        self._request(
            "PATCH",
            self.schema.roles_table,
            query=[(self.schema.role_id_column, f"eq.{role_id}")],
            payload={self.schema.domain_tags_column: domain_tags},
            prefer="return=minimal",
        )

    def _paged_get(
        self,
        table: str,
        select: str,
        extra_query: Sequence[tuple[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        start = 0
        while True:
            end = start + BATCH_SIZE - 1
            page = self._request(
                "GET",
                table,
                query=[("select", select), *(extra_query or [])],
                extra_headers={
                    "Range-Unit": "items",
                    "Range": f"{start}-{end}",
                },
            )
            if not page:
                break
            rows.extend(page)
            if len(page) < BATCH_SIZE:
                break
            start += BATCH_SIZE
        return rows

    def _request(
        self,
        method: str,
        table: str,
        query: Iterable[tuple[str, str]] | None = None,
        payload: Any | None = None,
        prefer: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        encoded_table = urllib.parse.quote(table, safe="")
        url = f"{self.rest_url}/{encoded_table}"
        if query:
            url += "?" + urllib.parse.urlencode(list(query))

        body = None
        headers = self._auth_headers()
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer
        if extra_headers:
            headers.update(extra_headers)

        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            raise SupabaseError(
                format_supabase_error(error.code, method, table, error_body)
            ) from error
        except urllib.error.URLError as error:
            raise SupabaseError(
                f"Could not reach Supabase REST API for table '{table}': {error.reason}"
            ) from error

        if not response_body:
            return None

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as error:
            raise SupabaseError(
                f"Supabase returned non-JSON data for table '{table}'."
            ) from error

    def _auth_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "apikey": self.service_role_key,
            "User-Agent": "career-compass-domain-tagger/1.0",
        }
        if not self.service_role_key.startswith(("sb_secret_", "sb_publishable_")):
            headers["Authorization"] = f"Bearer {self.service_role_key}"
        return headers


def format_supabase_error(
    status_code: int,
    method: str,
    table: str,
    response_body: str,
) -> str:
    try:
        error_json = json.loads(response_body)
    except json.JSONDecodeError:
        detail = response_body.strip()
    else:
        parts = [
            str(error_json.get("message") or "").strip(),
            str(error_json.get("details") or "").strip(),
            str(error_json.get("hint") or "").strip(),
        ]
        detail = " ".join(part for part in parts if part)

    if not detail:
        detail = "No response body returned."

    return (
        f"Supabase {method} failed for table '{table}' "
        f"with HTTP {status_code}: {detail}"
    )


def get_required_env() -> tuple[str, str]:
    load_dotenv_file(Path(".env"))
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    missing = []
    if not supabase_url:
        missing.append("SUPABASE_URL")
    if not service_role_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required environment variable(s): {joined}")
    if service_role_key.startswith("sb_publishable_"):
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY must be a secret key "
            "(sb_secret_...) or legacy service_role JWT, not a publishable key."
        )

    return supabase_url, service_role_key


def attach_role_skills(
    roles: Sequence[RoleRecord],
    skills_by_role_id: dict[str, list[str]],
) -> None:
    for role in roles:
        role.role_skills = skills_by_role_id.get(str(role.role_id), [])


def attach_role_certifications(
    roles: Sequence[RoleRecord],
    certifications_by_role_id: dict[str, list[str]],
) -> None:
    for role in roles:
        role.role_certifications = certifications_by_role_id.get(str(role.role_id), [])


def print_summary(
    classifications: Sequence[ClassificationResult],
    stats: UpdateStats,
    taxonomy: dict[str, TagDefinition],
    dry_run: bool,
    review_output: Path,
    taxonomy_output: Path,
) -> None:
    auto_added = [
        tag.slug
        for tag in taxonomy.values()
        if tag.source == "discovered" and tag.status == "auto_added"
    ]
    needs_review = [
        tag.slug
        for tag in taxonomy.values()
        if tag.source == "discovered" and tag.status == "needs_review"
    ]

    if dry_run:
        print("Dry run only. No database writes were made.")
    print(f"Roles reviewed: {len(classifications)}")
    print(f"Roles updated: {stats.roles_updated}")
    print(f"Roles that would update in dry run: {stats.roles_would_update}")
    print(f"Roles unchanged: {stats.roles_unchanged}")
    print(f"Roles skipped because domain_tags already exists: {stats.roles_skipped_existing}")
    print(f"Roles without assigned tags: {stats.roles_without_tags}")
    print(
        "Roles needing human review: "
        f"{sum(1 for result in classifications if result.needs_human_review)}"
    )
    print(f"Auto-added discovered tags: {', '.join(auto_added) if auto_added else 'none'}")
    print(f"Discovered tags needing review: {', '.join(needs_review) if needs_review else 'none'}")
    print(f"Review CSV: {review_output}")
    print(f"Taxonomy CSV: {taxonomy_output}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time database enrichment: assign deterministic Phase 3 "
            "domain tags to career_roles."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and score roles, write CSV outputs, but do not update Supabase.",
    )
    parser.add_argument(
        "--only-untagged",
        action="store_true",
        help="Review and update only roles where career_roles.domain_tags is empty.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-empty domain_tags values when the score changes.",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=Path("data/domain_tags_review.csv"),
        help="Path for the human review CSV.",
    )
    parser.add_argument(
        "--taxonomy-output",
        type=Path,
        default=Path("data/domain_tags_taxonomy.generated.csv"),
        help="Path for the generated taxonomy CSV.",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=Path("data/domain_tags_overrides.csv"),
        help="Optional manual override CSV with role_id, job_title, domain_tags, notes.",
    )
    parser.add_argument(
        "--no-discover-new-tags",
        action="store_true",
        help="Use only seed taxonomy tags plus manual overrides.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.force and args.only_untagged:
        parser.error("--force cannot be combined with --only-untagged")

    try:
        supabase_url, service_role_key = get_required_env()
        client = SupabaseRestClient(supabase_url, service_role_key)
        client.validate_schema()
        roles = client.list_roles()
        attach_role_skills(roles, client.list_role_skills_by_role_id())
        attach_role_certifications(roles, client.list_role_certifications_by_role_id())

        taxonomy = build_taxonomy(
            roles,
            discover_new_tags=not args.no_discover_new_tags,
        )
        overrides = load_manual_overrides(args.overrides, taxonomy)
        classifications = classify_roles(
            roles,
            taxonomy,
            overrides=overrides,
            only_untagged=args.only_untagged,
        )

        write_taxonomy_csv(taxonomy, args.taxonomy_output)
        write_review_csv(classifications, args.review_output)
        stats = update_domain_tags(
            classifications,
            client,
            dry_run=args.dry_run,
            force=args.force,
        )
        print_summary(
            classifications,
            stats,
            taxonomy,
            args.dry_run,
            args.review_output,
            args.taxonomy_output,
        )
        return 0
    except (ValueError, SupabaseError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
