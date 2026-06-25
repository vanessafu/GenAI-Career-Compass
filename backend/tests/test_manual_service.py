import pytest

from backend.app.features.cv_confirmation.manual_schemas import (
    ManualCVInput,
    ManualEducationInput,
    ManualExperienceInput,
    ManualProjectInput,
)
from backend.app.features.cv_confirmation.manual_service import (
    ManualCVValidationError,
    build_cv_data_from_manual_input,
)
from backend.app.features.cv_parsing.schemas import Language


def test_minimum_signal_required():
    with pytest.raises(ManualCVValidationError):
        build_cv_data_from_manual_input(ManualCVInput())


def test_current_role_alone_is_enough():
    cv = build_cv_data_from_manual_input(ManualCVInput(current_role="  Backend Developer  "))
    assert cv.personal_info.current_role == "Backend Developer"
    assert cv.source is not None and cv.source.filename == "manual_entry"
    assert cv.metadata.parsing_confidence == 0.0


def test_technical_skill_alone_is_enough():
    cv = build_cv_data_from_manual_input(ManualCVInput(technical_skills=["Python"]))
    assert [s.name for s in cv.skills_extracted.technical_skills] == ["Python"]


def test_full_mapping_and_profile_summary():
    cv = build_cv_data_from_manual_input(
        ManualCVInput(
            current_role="Engineer",
            seniority_level="Senior",
            years_of_experience=6,
            summary="  Builds reliable services.  ",
            education=[ManualEducationInput(degree_type="MSc", institution="TUM")],
            experience=[ManualExperienceInput(role="Dev", organization="Acme")],
            technical_skills=["Python", "Go"],
            soft_skills=["Communication"],
            languages=[Language(language="English", level="C2")],
            interests=["Open source"],
            projects=[ManualProjectInput(title="Pipeline", technologies=["Kafka"])],
        )
    )
    assert cv.profile_summary.current_seniority_level == "Senior"
    assert cv.profile_summary.years_of_experience == 6
    assert cv.profile_summary.summary == "Builds reliable services."
    assert cv.education[0].degree_type == "MSc"
    assert cv.experience[0].organization == "Acme"
    assert cv.projects[0].technologies == ["Kafka"]
    assert cv.skills_extracted.languages[0].language == "English"


def test_trimming_dedup_and_blank_filtering():
    cv = build_cv_data_from_manual_input(
        ManualCVInput(
            current_role="Engineer",
            technical_skills=["Python", " python ", "", "Go"],
            interests=["AI", "ai", "  "],
            education=[ManualEducationInput(degree_type="   ")],
            experience=[ManualExperienceInput(role="  ")],
        )
    )
    assert [s.name for s in cv.skills_extracted.technical_skills] == ["Python", "Go"]
    assert cv.interests == ["AI"]
    assert cv.education == []
    assert cv.experience == []
