from backend.app.features.cv_parsing.schemas import (
    CVData,
    Education,
    Experience,
    PersonalInfo,
    SkillsExtracted,
    TechnicalSkill,
)


def ask_optional(prompt: str) -> str | None:
    value = input(prompt).strip()
    return value or None


def ask_int_optional(prompt: str) -> int | None:
    value = input(prompt).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print("Please enter a whole number, or leave it blank.")
        return ask_int_optional(prompt)


def ask_comma_list(prompt: str) -> list[str]:
    value = input(prompt).strip()
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def collect_education() -> list[Education]:
    education: list[Education] = []
    print("\nEducation")
    while True:
        degree_type = ask_optional("Degree type (blank to stop): ")
        if degree_type is None:
            break

        education.append(
            Education(
                degree_type=degree_type,
                field_of_study=ask_optional("Field of study: "),
                institution=ask_optional("Institution: "),
            )
        )
    return education


def collect_experience() -> list[Experience]:
    experience: list[Experience] = []
    print("\nWork Experience")
    while True:
        role = ask_optional("Role (blank to stop): ")
        if role is None:
            break

        experience.append(
            Experience(
                role=role,
                organization=ask_optional("Organization: "),
                industry=ask_optional("Industry: "),
                duration_months=ask_int_optional("Duration in months: "),
                core_responsibilities=ask_comma_list("Responsibilities, comma-separated: "),
                contextual_skills=ask_comma_list("Skills used, comma-separated: "),
            )
        )
    return experience


def collect_skills() -> SkillsExtracted:
    print("\nSkills")
    technical_skills = [
        TechnicalSkill(name=skill)
        for skill in ask_comma_list("Technical skills, comma-separated: ")
    ]
    soft_skills = ask_comma_list("Soft skills, comma-separated: ")
    return SkillsExtracted(technical_skills=technical_skills, soft_skills=soft_skills)


def collect_manual_cv_data() -> CVData:
    print("Manual profile setup")
    print("Leave fields blank when you do not want to provide them yet.")

    current_role = ask_optional("\nCurrent role: ")
    cv_data = CVData(
        personal_info=PersonalInfo(current_role=current_role),
        education=collect_education(),
        experience=collect_experience(),
        skills_extracted=collect_skills(),
    )
    return cv_data
