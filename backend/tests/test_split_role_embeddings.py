from __future__ import annotations

import unittest
from pathlib import Path

from backend.scripts.role_embeddings import (
    build_capability_embedding_text,
    build_intent_embedding_text,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class SplitRoleEmbeddingTextTests(unittest.TestCase):
    def test_capability_embedding_text_contains_role_requirements_only(self) -> None:
        text = build_capability_embedding_text(
            title="Senior Backend Engineer",
            description="Build APIs and mentor engineers for a payments platform.",
            skills_text="java, postgresql, restful apis",
            certifications="AWS Certified Developer - Associate",
            raw_certifications="AWS Certified Developer - Associate",
        )

        self.assertIn("Job title: Senior Backend Engineer", text)
        self.assertIn("Required skills: java, postgresql, restful apis", text)
        self.assertIn("Certifications: AWS Certified Developer - Associate", text)
        self.assertIn("Responsibilities: Build APIs", text)

    def test_intent_embedding_text_contains_direction_domain_and_context(self) -> None:
        text = build_intent_embedding_text(
            title="Senior Backend Engineer",
            description="Build APIs and mentor engineers for a payments platform.",
            domain_tags="backend,cloud,architecture",
        )

        self.assertIn("Career direction: Senior Backend Engineer", text)
        self.assertIn("Domain tags: backend,cloud,architecture", text)
        self.assertIn("Role context: Build APIs", text)
        self.assertNotIn("Required skills:", text)
        self.assertNotIn("Certifications:", text)


class SplitRoleEmbeddingSchemaTests(unittest.TestCase):
    def test_role_embedding_script_writes_split_role_vectors_and_texts(self) -> None:
        source = (REPO_ROOT / "backend" / "scripts" / "role_embeddings.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("capability_embedding", source)
        self.assertIn("intent_embedding", source)
        self.assertIn("capability_embedding_text", source)
        self.assertIn("intent_embedding_text", source)
        self.assertIn("FROM role_skills", source)
        self.assertIn("certifications_mapping", source)
        self.assertNotIn("only-certification", source)
        self.assertNotIn("certifications ADD COLUMN IF NOT EXISTS embedding", source)

    def test_matcher_reads_split_role_vectors(self) -> None:
        source = (
            REPO_ROOT
            / "backend"
            / "app"
            / "features"
            / "role_matching"
            / "service.py"
        ).read_text(encoding="utf-8")

        self.assertIn("capability_embedding <=>", source)
        self.assertIn("intent_embedding <=>", source)
        self.assertIn("capability_embedding IS NOT NULL", source)
        self.assertIn("intent_embedding IS NOT NULL", source)
        self.assertNotIn("1 - (embedding <=>", source)

    def test_certification_gap_analysis_no_longer_reads_cert_embeddings(self) -> None:
        source = (
            REPO_ROOT
            / "backend"
            / "app"
            / "features"
            / "role_matching"
            / "gap_analysis.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("c.embedding", source)
        self.assertNotIn("encode_documents(user_certs)", source)
        self.assertNotIn("rc.get(\"embedding\")", source)


if __name__ == "__main__":
    unittest.main()
