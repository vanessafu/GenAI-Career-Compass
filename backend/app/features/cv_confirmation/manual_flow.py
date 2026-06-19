from backend.app.features.cv_parsing.schemas import (
    Certification,
    CVData,
    Education,
    Experience,
    PersonalInfo,
    Project,
    SkillsExtracted,
    TechnicalSkill,
    Thesis,
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


def collect_projects() -> list[Project]:
    projects: list[Project] = []
    print("\nProjects")
    while True:
        title = ask_optional("Project title (blank to stop): ")
        if title is None:
            break

        projects.append(
            Project(
                title=title,
                description=ask_optional("Description: "),
                organization=ask_optional("Organization/context: "),
                role=ask_optional("Your role: "),
                technologies=ask_comma_list("Technologies, comma-separated: "),
                outcomes=ask_comma_list("Outcomes, comma-separated: "),
                links=ask_comma_list("Links, comma-separated: "),
            )
        )
    return projects


def collect_certifications() -> list[Certification]:
    certifications: list[Certification] = []
    print("\nCertifications")
    while True:
        name = ask_optional("Certification name (blank to stop): ")
        if name is None:
            break

        certifications.append(
            Certification(
                name=name,
                issuing_organization=ask_optional("Issuing organization: "),
                issue_date=ask_optional("Issue date: "),
                expiration_date=ask_optional("Expiration date: "),
                credential_id=ask_optional("Credential ID: "),
                credential_url=ask_optional("Credential URL: "),
            )
        )
    return certifications


def collect_thesis() -> list[Thesis]:
    theses: list[Thesis] = []
    print("\nThesis")
    while True:
        title = ask_optional("Thesis title (blank to stop): ")
        if title is None:
            break

        theses.append(
            Thesis(
                title=title,
                degree_type=ask_optional("Degree type: "),
                institution=ask_optional("Institution: "),
                supervisor=ask_optional("Supervisor: "),
                description=ask_optional("Description: "),
                technologies=ask_comma_list("Technologies, comma-separated: "),
                grade=ask_optional("Grade: "),
            )
        )
    return theses


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
        projects=collect_projects(),
        certifications=collect_certifications(),
        thesis=collect_thesis(),
        skills_extracted=collect_skills(),
    )
    return cv_data
