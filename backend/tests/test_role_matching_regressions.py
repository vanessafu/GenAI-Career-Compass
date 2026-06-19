from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.app.features.cv_confirmation.schemas import (
    ConfirmationMetadata,
    ConfirmedCVData,
)
from backend.app.features.cv_parsing.schemas import (
    Certification,
    CVData,
    Experience,
    PersonalInfo,
    ProfileSummary,
    Project,
    SkillsExtracted,
    TechnicalSkill,
    Thesis,
)
from backend.app.features.role_matching.gap_analysis import _user_certs, _user_seniority
from backend.app.features.role_matching.service import extract_user_skills
from backend.app.features.role_matching.skill_ontology import SkillOntology


REPO_ROOT = Path(__file__).resolve().parents[2]


class SkillOntologyTests(unittest.TestCase):
    def test_missing_ontology_file_falls_back_to_exact_skill_matching(self) -> None:
        ontology = SkillOntology(path=Path("missing-ontology-file.json"))

        coverage, matched, gaps = ontology.compute_coverage(
            "Python, SQL, FastAPI",
            ["python", "sql"],
        )

        self.assertEqual(coverage, 2 / 3)
        self.assertEqual(matched, ["Python", "SQL"])
        self.assertEqual(
            gaps,
            [
                {
                    "required_skill": "FastAPI",
                    "user_closest_skill": None,
                    "transferability": 0.0,
                    "severity": "high",
                }
            ],
        )

    def test_ontology_file_still_supports_synonyms_and_implied_skills(self) -> None:
        payload = {
            "react": {
                "name": "React",
                "synonyms": ["React.js"],
                "impliesKnowingSkills": ["JavaScript"],
            },
            "javascript": {
                "name": "JavaScript",
                "synonyms": ["JS"],
                "impliesKnowingSkills": [],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ontology.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            ontology = SkillOntology(path=path)

        coverage, matched, gaps = ontology.compute_coverage(
            "React.js, JavaScript",
            ["react"],
        )

        self.assertEqual(coverage, 1.0)
        self.assertEqual(matched, ["React", "JavaScript"])
        self.assertEqual(gaps, [])


class SupabaseSchemaDriftTests(unittest.TestCase):
    def test_role_embedding_script_uses_live_career_role_columns(self) -> None:
        source = (REPO_ROOT / "backend" / "scripts" / "role_embeddings.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("capability_embedding", source)
        self.assertIn("intent_embedding", source)
        self.assertIn("capability_embedding_text", source)
        self.assertIn("intent_embedding_text", source)
        self.assertIn("c.raw_certifications", source)
        self.assertNotIn("c.certification_tags", source)

    def test_certifications_are_not_embedded_separately(self) -> None:
        source = (REPO_ROOT / "backend" / "scripts" / "role_embeddings.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("certifications_mapping", source)
        self.assertNotIn("only-certification", source)
        self.assertNotIn("store_cert_embeddings", source)
        self.assertNotIn("certifications ADD COLUMN IF NOT EXISTS embedding", source)
        self.assertNotIn("role_certifications", source)

    def test_gap_analysis_uses_split_certifications_and_live_esco_name(self) -> None:
        source = (
            REPO_ROOT
            / "backend"
            / "app"
            / "features"
            / "role_matching"
            / "gap_analysis.py"
        ).read_text(encoding="utf-8")

        self.assertIn("certifications_mapping", source)
        self.assertIn("JOIN certifications", source)
        self.assertIn("eo.name", source)
        self.assertNotIn("FROM role_certifications", source)
        self.assertNotIn("eo.esco_title", source)


class RoleMatchingInputShapeTests(unittest.TestCase):
    def _confirmed_profile(self) -> ConfirmedCVData:
        cv_data = CVData(
            personal_info=PersonalInfo(current_role="Backend Developer"),
            profile_summary=ProfileSummary(
                summary="Builds reliable APIs and data services.",
                current_seniority_level="senior",
                years_of_experience=6,
            ),
            skills_extracted=SkillsExtracted(
                technical_skills=[
                    TechnicalSkill(name="Python"),
                    TechnicalSkill(name="PostgreSQL"),
                ]
            ),
            certifications=[
                Certification(
                    name="AWS Certified Developer - Associate",
                    issuing_organization="Amazon Web Services",
                )
            ],
            experience=[
                Experience(
                    role="Backend Developer",
                    duration_months=48,
                    core_responsibilities=["Built REST APIs"],
                    contextual_skills=["FastAPI"],
                )
            ],
            projects=[
                Project(
                    title="Payment Gateway",
                    description="Migrated a monolith into services.",
                    technologies=["Docker", "REST"],
                )
            ],
            thesis=[
                Thesis(
                    title="Event-driven systems",
                    description="Studied reliable async workflows.",
                    technologies=["Kafka"],
                )
            ],
        )
        return ConfirmedCVData(
            confirmed_cv_data=cv_data,
            confirmation_metadata=ConfirmationMetadata(),
        )

    def test_legacy_cv_wrapper_skill_extraction_stays_available_for_gap_analysis(self) -> None:
        confirmed = self._confirmed_profile()

        skills = extract_user_skills(confirmed)

        self.assertEqual(
            skills,
            ["Python", "PostgreSQL", "Docker", "REST", "Kafka", "FastAPI"],
        )

    def test_gap_analysis_reads_certifications_and_seniority_from_wrapper(self) -> None:
        confirmed = self._confirmed_profile()

        self.assertEqual(_user_certs(confirmed), ["AWS Certified Developer - Associate"])
        self.assertEqual(_user_seniority(confirmed), ("senior", 6))


if __name__ == "__main__":
    unittest.main()
