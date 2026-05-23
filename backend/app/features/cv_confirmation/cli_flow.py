import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.app.features.cv_confirmation.service import (
    add_list_item,
    build_confirmation_sections,
    get_value_at_path,
    remove_list_item,
    set_value_at_path,
    to_confirmed_cv_data,
)
from backend.app.features.cv_parsing.schemas import CVData


def load_cv_data(path: Path) -> CVData:
    return CVData.model_validate_json(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_json_input(raw_value: str) -> Any:
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def validate_cv_update(data: dict[str, Any]) -> None:
    CVData.model_validate(data)


def format_path(path: list[str | int]) -> str:
    return ".".join(str(part) for part in path)


def prompt_for_number(prompt: str, upper_bound: int) -> int | None:
    raw_index = input(prompt).strip()
    try:
        index = int(raw_index) - 1
    except ValueError:
        print("Please enter a number.")
        return None

    if index < 0 or index >= upper_bound:
        print("That number is outside the available range.")
        return None
    return index


def edit_value_at_path(data: dict[str, Any], path: list[str | int], edited_fields: list[str]) -> dict[str, Any]:
    current_value = get_value_at_path(data, path)
    print(f"Current value: {json.dumps(current_value, ensure_ascii=False)}")
    raw_value = input("New value (blank = null, JSON allowed): ").strip()
    new_value = None if raw_value == "" else parse_json_input(raw_value)
    updated_data = set_value_at_path(data, path, new_value)
    validate_cv_update(updated_data)
    edited_fields.append(format_path(path))
    print("Value updated.")
    return updated_data


def edit_dict_section(
    data: dict[str, Any],
    section_path: list[str | int],
    section_value: dict[str, Any],
    edited_fields: list[str],
) -> dict[str, Any]:
    fields = list(section_value.keys())
    if not fields:
        print("This section has no editable fields yet.")
        return data

    print("\nWhich field do you want to edit?")
    for index, field_name in enumerate(fields, start=1):
        value = section_value[field_name]
        print(f"{index}. {field_name}: {json.dumps(value, ensure_ascii=False)}")

    field_index = prompt_for_number("Field number: ", len(fields))
    if field_index is None:
        return data

    field_name = fields[field_index]
    return edit_value_at_path(data, [*section_path, field_name], edited_fields)


def edit_list_item(
    data: dict[str, Any],
    section_path: list[str | int],
    section_value: list[Any],
    edited_fields: list[str],
) -> dict[str, Any]:
    if not section_value:
        print("This list is empty. Use add item first.")
        return data

    item_index = prompt_for_number("Item number to edit: ", len(section_value))
    if item_index is None:
        return data

    item = section_value[item_index]
    item_path = [*section_path, item_index]
    if isinstance(item, dict):
        return edit_dict_section(data, item_path, item, edited_fields)

    return edit_value_at_path(data, item_path, edited_fields)


def edit_section_as_json(
    data: dict[str, Any],
    section_path: list[str | int],
    edited_fields: list[str],
) -> dict[str, Any]:
    print("Paste replacement JSON for this section. For strings, include quotes.")
    raw_value = input("New value: ").strip()
    new_value = parse_json_input(raw_value)
    updated_data = set_value_at_path(data, section_path, new_value)
    validate_cv_update(updated_data)
    edited_fields.append(format_path(section_path))
    print("Section updated.")
    return updated_data


def confirm_cv_interactively(cv_data: CVData, assume_yes: bool = False) -> tuple[CVData, list[str], list[str], list[str]]:
    data = cv_data.model_dump(mode="json")
    confirmed_sections: list[str] = []
    skipped_sections: list[str] = []
    edited_fields: list[str] = []

    for section in build_confirmation_sections():
        if assume_yes:
            confirmed_sections.append(section.section_id)
            continue

        while True:
            section_value = get_value_at_path(data, section.path)
            print(f"\n=== {section.title} ===")
            print(json.dumps(section_value, indent=2, ensure_ascii=False))

            options = "[c] confirm  [e] edit"
            if isinstance(section_value, list):
                options += "  [a] add item  [r] remove item"
            options += "  [j] replace section JSON"
            options += "  [s] skip  [q] quit: "
            choice = input(f"\n{options}").strip().lower()

            if choice in {"c", "confirm", ""}:
                confirmed_sections.append(section.section_id)
                break
            if choice in {"s", "skip"}:
                skipped_sections.append(section.section_id)
                break
            if choice in {"q", "quit"}:
                raise KeyboardInterrupt("Confirmation flow cancelled by user.")
            if choice in {"e", "edit"}:
                try:
                    if isinstance(section_value, dict):
                        data = edit_dict_section(data, section.path, section_value, edited_fields)
                    elif isinstance(section_value, list):
                        data = edit_list_item(data, section.path, section_value, edited_fields)
                    else:
                        data = edit_value_at_path(data, section.path, edited_fields)
                except (json.JSONDecodeError, ValidationError, TypeError, KeyError, IndexError) as exc:
                    print(f"Invalid update: {exc}")
                continue

            if choice in {"j", "json"}:
                try:
                    data = edit_section_as_json(data, section.path, edited_fields)
                except (json.JSONDecodeError, ValidationError, TypeError, KeyError, IndexError) as exc:
                    print(f"Invalid update: {exc}")
                continue

            if choice in {"a", "add"} and isinstance(section_value, list):
                raw_value = input("New item as JSON or plain text: ").strip()
                try:
                    updated_data = add_list_item(data, section.path, parse_json_input(raw_value))
                    validate_cv_update(updated_data)
                except (ValidationError, TypeError, KeyError, IndexError) as exc:
                    print(f"Invalid item: {exc}")
                    continue

                data = updated_data
                edited_fields.append(format_path(section.path))
                print("Item added.")
                continue

            if choice in {"r", "remove"} and isinstance(section_value, list):
                try:
                    index = prompt_for_number("Item number to remove: ", len(section_value))
                    if index is None:
                        continue
                    updated_data = remove_list_item(data, section.path, index)
                    validate_cv_update(updated_data)
                except (ValueError, ValidationError, TypeError, KeyError, IndexError) as exc:
                    print(f"Invalid item number: {exc}")
                    continue

                data = updated_data
                edited_fields.append(format_path(section.path))
                print("Item removed.")
                continue

            print("Please choose one of the listed options.")

    return CVData.model_validate(data), confirmed_sections, skipped_sections, edited_fields


def confirm_json_file(input_path: Path, output_path: Path, assume_yes: bool = False) -> Path:
    cv_data = load_cv_data(input_path)
    confirmed_cv, confirmed_sections, skipped_sections, edited_fields = confirm_cv_interactively(
        cv_data,
        assume_yes=assume_yes,
    )
    result = to_confirmed_cv_data(
        confirmed_cv,
        confirmed_sections=confirmed_sections,
        skipped_sections=skipped_sections,
        edited_fields=edited_fields,
    )
    save_json(output_path, result.model_dump(mode="json"))
    return output_path
