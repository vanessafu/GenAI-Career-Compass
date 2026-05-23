from copy import deepcopy
from typing import Any

from backend.app.features.cv_confirmation.schemas import (
    ConfirmationMetadata,
    ConfirmationSection,
    ConfirmedCVData,
)
from backend.app.features.cv_parsing.schemas import CVData


def build_confirmation_sections() -> list[ConfirmationSection]:
    return [
        ConfirmationSection(
            section_id="personal_info",
            title="Personal Info",
            path=["personal_info"],
        ),
        ConfirmationSection(
            section_id="profile_summary",
            title="Profile Summary",
            path=["profile_summary"],
        ),
        ConfirmationSection(section_id="experience", title="Experience", path=["experience"]),
        ConfirmationSection(section_id="education", title="Education", path=["education"]),
        ConfirmationSection(
            section_id="technical_skills",
            title="Technical Skills",
            path=["skills_extracted", "technical_skills"],
        ),
        ConfirmationSection(
            section_id="soft_skills",
            title="Soft Skills",
            path=["skills_extracted", "soft_skills"],
        ),
        ConfirmationSection(
            section_id="languages",
            title="Languages",
            path=["skills_extracted", "languages"],
        ),
        ConfirmationSection(section_id="interests", title="Interests", path=["interests"]),
        ConfirmationSection(
            section_id="unmapped_information",
            title="Unmapped Information",
            path=["unmapped_information"],
        ),
    ]


def get_value_at_path(data: dict[str, Any], path: list[str | int]) -> Any:
    current: Any = data
    for part in path:
        current = current[part]
    return current


def set_value_at_path(data: dict[str, Any], path: list[str | int], value: Any) -> dict[str, Any]:
    updated = deepcopy(data)
    current: Any = updated
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value
    return updated


def add_list_item(data: dict[str, Any], path: list[str | int], value: Any) -> dict[str, Any]:
    updated = deepcopy(data)
    target = get_value_at_path(updated, path)
    if not isinstance(target, list):
        raise TypeError("Target path is not a list.")
    target.append(value)
    return updated


def remove_list_item(data: dict[str, Any], path: list[str | int], index: int) -> dict[str, Any]:
    updated = deepcopy(data)
    target = get_value_at_path(updated, path)
    if not isinstance(target, list):
        raise TypeError("Target path is not a list.")
    del target[index]
    return updated


def to_confirmed_cv_data(
    cv_data: CVData,
    confirmed_sections: list[str],
    skipped_sections: list[str],
    edited_fields: list[str],
) -> ConfirmedCVData:
    return ConfirmedCVData(
        confirmed_cv_data=cv_data,
        confirmation_metadata=ConfirmationMetadata(
            confirmed_sections=confirmed_sections,
            skipped_sections=skipped_sections,
            edited_fields=edited_fields,
        ),
    )
