from backend.app.features.cv_parsing.schemas import (
    Certification,
    CVData,
    Education,
    Experience,
    PersonalInfo,
    Project,
    Thesis,
    UnmappedInformation,
)

# Substrings that mark an unmapped item as personally identifying; such items are
# dropped from the privacy-stripped CV entirely.
_PII_UNMAPPED_TERMS = (
    "address",
    "birth",
    "contact",
    "date of birth",
    "email",
    "gender",
    "nationality",
    "phone",
    "website",
)


def _is_pii_unmapped(item: UnmappedInformation) -> bool:
    searchable = " ".join(
        part.lower()
        for part in (item.label, item.source_section, item.reason_not_mapped)
        if part
    )
    if any(term in searchable for term in _PII_UNMAPPED_TERMS):
        return True
    value = item.value.strip()
    if "http://" in value.lower() or "https://" in value.lower() or "@" in value:
        return True
    return False


def privacy_strip_cv_data(cv_data: CVData) -> CVData:
    """Return the same CVData schema with personal identifiers removed.

    Keeps every career-relevant signal (roles, skills, responsibilities, fields of
    study, technologies, ...) but nulls direct identifiers: names, contacts, links,
    locations, organization names, institutions, supervisors, credentials, grades,
    and the raw source document text.
    """
    return CVData(
        source=None,
        metadata=cv_data.metadata,
        personal_info=PersonalInfo(current_role=cv_data.personal_info.current_role),
        profile_summary=cv_data.profile_summary,
        experience=[
            Experience(
                role=experience.role,
                industry=experience.industry,
                duration_months=experience.duration_months,
                core_responsibilities=experience.core_responsibilities,
                contextual_skills=experience.contextual_skills,
            )
            for experience in cv_data.experience
        ],
        education=[
            Education(
                entry_type=education.entry_type,
                degree_type=education.degree_type,
                field_of_study=education.field_of_study,
                start_date=education.start_date,
                end_date=education.end_date,
                courses=education.courses,
            )
            for education in cv_data.education
        ],
        projects=[
            Project(
                title=project.title,
                description=project.description,
                technologies=project.technologies,
                outcomes=project.outcomes,
                start_date=project.start_date,
                end_date=project.end_date,
            )
            for project in cv_data.projects
        ],
        certifications=[
            Certification(
                name=certification.name,
                issue_date=certification.issue_date,
                expiration_date=certification.expiration_date,
            )
            for certification in cv_data.certifications
        ],
        thesis=[
            Thesis(
                title=thesis.title,
                degree_type=thesis.degree_type,
                description=thesis.description,
                technologies=thesis.technologies,
            )
            for thesis in cv_data.thesis
        ],
        skills_extracted=cv_data.skills_extracted,
        interests=cv_data.interests,
        unmapped_information=[
            item for item in cv_data.unmapped_information if not _is_pii_unmapped(item)
        ],
    )
