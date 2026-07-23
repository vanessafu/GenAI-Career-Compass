import pytest
from pydantic import ValidationError

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


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "technical_skills": ["Python"],
                "interests": ["Cloud"],
            },
            "current role",
        ),
        (
            {
                "current_role": "Engineer",
                "interests": ["Cloud"],
            },
            "technical skill",
        ),
        (
            {
                "current_role": "Engineer",
                "technical_skills": ["Python"],
            },
            "interest",
        ),
    ],
)
def test_required_manual_profile_signal(payload, message):
    with pytest.raises(ManualCVValidationError, match=message):
        build_cv_data_from_manual_input(ManualCVInput(**payload))


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
            projects=[
                ManualProjectInput(
                    title="Pipeline",
                    description="Data platform",
                    technologies=["Kafka"],
                    start_date="2023",
                    end_date="2024",
                )
            ],
            certifications=[
                {
                    "name": "AWS Certified Developer",
                    "issuing_organization": "AWS",
                    "issue_date": "2023",
                }
            ],
        )
    )
    assert cv.profile_summary.current_seniority_level == "Senior"
    assert cv.profile_summary.years_of_experience == 6
    assert cv.profile_summary.summary == "Builds reliable services."
    assert cv.education[0].degree_type == "MSc"
    assert cv.experience[0].organization == "Acme"
    assert cv.projects[0].technologies == ["Kafka"]
    assert cv.certifications[0].name == "AWS Certified Developer"
    assert cv.skills_extracted.languages[0].language == "English"
    assert cv.unmapped_information == []


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


def test_manual_payload_bounds_and_unknown_fields():
    with pytest.raises(ValidationError):
        ManualCVInput(
            current_role="Engineer",
            technical_skills=["Python"] * 51,
            interests=["Cloud"],
        )
    with pytest.raises(ValidationError):
        ManualCVInput(
            current_role="Engineer",
            technical_skills=["Python"],
            interests=["Cloud"],
            target_constraints=["Remote"],
        )