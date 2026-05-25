import argparse
import asyncio
import json
from pathlib import Path

from backend.app.features.cv_confirmation.cli_flow import confirm_cv_interactively, confirm_json_file
from backend.app.features.cv_confirmation.manual_flow import collect_manual_cv_data
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_confirmation.service import to_confirmed_cv_data
from backend.app.features.cv_parsing.schemas import SourceDocument
from backend.app.features.cv_parsing.service import (
    extract_text_from_pdf_bytes,
    parse_cv_to_pydantic,
)
from backend.app.features.prompt_engineering.artifact_service import (
    save_embedding_input_text_artifact,
    save_identity_followups_artifact,
)
from backend.app.features.prompt_engineering.embedding_preparation_service import (
    build_embedding_input,
)
from backend.app.features.prompt_engineering.schemas import (
    EmbeddingInputResponse,
    StarterProfileResponse,
)
from backend.app.features.prompt_engineering.service import generate_starter_profile


def default_output_path(input_path: Path, suffix: str) -> Path:
    return Path("outputs") / f"{input_path.stem}_{suffix}.json"


def read_pdf_text(pdf_path: Path) -> str:
    return extract_text_from_pdf_bytes(pdf_path.read_bytes())


def write_text_output(output_path: Path, text: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def write_json_output(output_path: Path, payload: dict) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def load_confirmed_profile(json_path: Path) -> ConfirmedCVData:
    return ConfirmedCVData.model_validate_json(json_path.read_text(encoding="utf-8"))


async def parse_cv_file(pdf_path: Path, output_path: Path | None = None) -> Path:
    raw_text = read_pdf_text(pdf_path)
    if not raw_text:
        raise ValueError("The PDF does not contain readable text.")

    parsed_cv = await parse_cv_to_pydantic(raw_text)
    parsed_cv.source = SourceDocument(filename=pdf_path.name, extracted_text=raw_text)

    target_path = output_path or default_output_path(pdf_path, "parsed")
    return write_json_output(target_path, parsed_cv.model_dump(mode="json"))


async def confirm_cv_file(
    pdf_path: Path,
    output_path: Path | None = None,
    assume_yes: bool = False,
) -> Path:
    parsed_path = await parse_cv_file(pdf_path)
    target_path = output_path or default_output_path(pdf_path, "confirmed")
    return confirm_json_file(parsed_path, target_path, assume_yes=assume_yes)


def collect_manual_profile(output_path: Path, assume_yes: bool = False) -> Path:
    cv_data = collect_manual_cv_data()
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
    return write_json_output(output_path, result.model_dump(mode="json"))


async def generate_starter_profile_from_file(json_path: Path) -> StarterProfileResponse:
    confirmed_profile = load_confirmed_profile(json_path)
    return await generate_starter_profile(confirmed_profile)


def build_embedding_input_from_file(json_path: Path) -> EmbeddingInputResponse:
    confirmed_profile = load_confirmed_profile(json_path)
    return build_embedding_input(confirmed_profile)


def print_starter_profile(result: StarterProfileResponse) -> None:
    print("\nStarter identity:")
    print(result.starter_identity)
    print("\nFollow-up questions:")
    for index, question in enumerate(result.suggested_questions, start=1):
        print(f"{index}. {question.question}")
        for option in question.options:
            print(f"   - {option}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Career Compass backend CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract-text", help="Extract readable text from a PDF CV.")
    extract_parser.add_argument("pdf_path", type=Path)
    extract_parser.add_argument("-o", "--output", type=Path)

    parse_parser = subparsers.add_parser("parse-cv", help="Parse a PDF CV into structured JSON.")
    parse_parser.add_argument("pdf_path", type=Path)
    parse_parser.add_argument("-o", "--output", type=Path)

    confirm_json_parser = subparsers.add_parser(
        "confirm-json",
        help="Confirm an existing parsed CV JSON file.",
    )
    confirm_json_parser.add_argument("json_path", type=Path)
    confirm_json_parser.add_argument("-o", "--output", type=Path)
    confirm_json_parser.add_argument("--yes", action="store_true", help="Confirm all sections automatically.")

    confirm_cv_parser = subparsers.add_parser(
        "confirm-cv",
        help="Parse a PDF CV and run the confirmation flow.",
    )
    confirm_cv_parser.add_argument("pdf_path", type=Path)
    confirm_cv_parser.add_argument("-o", "--output", type=Path)
    confirm_cv_parser.add_argument("--yes", action="store_true", help="Confirm all sections automatically.")

    manual_parser = subparsers.add_parser(
        "manual-profile",
        help="Enter profile information manually and run the confirmation flow.",
    )
    manual_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("outputs/manual_profile_confirmed.json"),
    )
    manual_parser.add_argument("--yes", action="store_true", help="Confirm all sections automatically.")

    identity_parser = subparsers.add_parser(
        "identity-followups",
        help="Generate identity and follow-up questions from confirmed JSON.",
    )
    identity_parser.add_argument("json_path", type=Path)

    embedding_parser = subparsers.add_parser(
        "embedding-input",
        help="Build embedding input text from confirmed JSON.",
    )
    embedding_parser.add_argument("json_path", type=Path)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "extract-text":
        raw_text = read_pdf_text(args.pdf_path)
        if args.output:
            output_path = write_text_output(args.output, raw_text)
            print(f"Extracted text written to {output_path}")
        else:
            print(raw_text)
        return

    if args.command == "parse-cv":
        output_path = asyncio.run(parse_cv_file(args.pdf_path, args.output))
        print(f"Parsed CV written to {output_path}")
        return

    if args.command == "confirm-json":
        output_path = args.output or default_output_path(args.json_path, "confirmed")
        result_path = confirm_json_file(args.json_path, output_path, assume_yes=args.yes)
        print(f"Confirmed CV written to {result_path}")
        return

    if args.command == "confirm-cv":
        output_path = asyncio.run(confirm_cv_file(args.pdf_path, args.output, assume_yes=args.yes))
        print(f"Confirmed CV written to {output_path}")
        return

    if args.command == "manual-profile":
        output_path = collect_manual_profile(args.output, assume_yes=args.yes)
        print(f"Confirmed manual profile written to {output_path}")
        return

    if args.command == "identity-followups":
        result = asyncio.run(generate_starter_profile_from_file(args.json_path))
        print_starter_profile(result)
        output_path = save_identity_followups_artifact(args.json_path, result)
        print(f"\nIdentity and follow-up generation appended to {output_path}")
        return

    if args.command == "embedding-input":
        result = build_embedding_input_from_file(args.json_path)
        output_path = save_embedding_input_text_artifact(args.json_path, result)
        print(f"Embedding input text written to {output_path}")
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
