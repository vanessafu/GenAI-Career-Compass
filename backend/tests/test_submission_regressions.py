from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter

from backend.app.features.cv_parsing.service import extract_text_from_pdf_bytes
from backend.app.features.profile_pipeline.router import MAX_PDF_BYTES
from backend.app.features.role_matching import skill_ontology
from backend.app.features.role_matching.prepared_skills import (
    SkillEvidence,
    prepare_user_skills,
)
from backend.app.features.role_matching.skill_alignment import align_skills


def test_password_encrypted_pdf_is_rejected_as_invalid_input() -> None:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt("test-password")
    writer.write(output)

    with pytest.raises(ValueError, match="could not be read"):
        extract_text_from_pdf_bytes(output.getvalue())


def test_all_submission_cv_fixtures_extract_with_pypdf() -> None:
    cv_dir = Path(__file__).resolve().parents[2] / "test_data" / "cvs"
    fixtures = sorted(cv_dir.glob("*.pdf"))

    assert len(fixtures) == 9
    for fixture in fixtures:
        payload = fixture.read_bytes()
        assert len(payload) <= MAX_PDF_BYTES
        assert payload.startswith(b"%PDF-")
        assert extract_text_from_pdf_bytes(payload).strip(), fixture.name


def test_mind_synonym_gets_full_credit_in_both_matching_paths(monkeypatch) -> None:
    monkeypatch.setattr(skill_ontology, "_ontology", skill_ontology.SkillOntology())
    evidence = SkillEvidence(explicit_terms=["K8s"])

    prepared_result = align_skills(
        ["Kubernetes"],
        prepared=prepare_user_skills(evidence),
    )
    direct_result = align_skills(
        ["Kubernetes"],
        evidence=evidence,
        enable_ontology_tiers=True,
    )

    for result in (prepared_result, direct_result):
        assert result.coverage == 1.0
        assert result.matched_skills == ["kubernetes"]
        assert result.skill_gaps == []


def test_combined_embedding_skills_respect_collection_limit() -> None:
    from backend.app.core.validation import MAX_ITEMS
    from backend.app.features.cv_parsing.schemas import (
        CVData,
        SkillsExtracted,
        SoftSkill,
        TechnicalSkill,
    )
    from backend.app.features.profile_pipeline.service import build_embedding_profile
    from backend.app.features.profile_preparation.schemas import CareerIdentitySummary

    cv_data = CVData(
        skills_extracted=SkillsExtracted(
            technical_skills=[
                TechnicalSkill(name=f"Technical {index}") for index in range(40)
            ],
            soft_skills=[SoftSkill(name=f"Soft {index}", confidence=80) for index in range(40)],
        )
    )

    profile = build_embedding_profile(
        cv_data,
        CareerIdentitySummary(label="Engineer", summary="Builds reliable systems."),
    )

    assert len(profile.skills) == MAX_ITEMS
    assert profile.skills[:2] == ["Technical 0", "Technical 1"]
