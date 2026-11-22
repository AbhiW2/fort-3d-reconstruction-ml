import argparse
import json
import re
from pathlib import Path

import pymupdf

from rag_config import PDF_DATASETS, PROJECT_ROOT, RAW_DOCUMENTS_PATH, RAG_DATA_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract text from a PDF by page.")
    pdf_group = parser.add_mutually_exclusive_group()
    pdf_group.add_argument(
        "--pdf",
        type=Path,
        help="PDF path; relative paths are resolved from the Fort_project folder.",
    )
    pdf_group.add_argument(
        "--all",
        action="store_true",
        help="Extract every PDF registered in scripts\\rag_config.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSONL output path; relative paths use the Fort_project folder.",
    )
    return parser.parse_args()


def project_path(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def dataset_stem(pdf_path: Path) -> str:
    for dataset in PDF_DATASETS.values():
        if pdf_path.name.casefold() == dataset["filename"].casefold():
            return dataset["stem"]
    return re.sub(r"[^a-z0-9]+", "_", pdf_path.stem.lower()).strip("_")


def main() -> None:
    args = parse_args()
    if args.all and args.output:
        raise ValueError("--output cannot be used with --all")
    if args.all:
        pdf_paths = [
            RAW_DOCUMENTS_PATH / dataset["filename"]
            for dataset in PDF_DATASETS.values()
        ]
    else:
        pdf_paths = [
            project_path(args.pdf)
            if args.pdf
            else RAW_DOCUMENTS_PATH / PDF_DATASETS["purohit"]["filename"]
        ]

    for pdf_path in pdf_paths:
        if args.output:
            output_path = project_path(args.output)
        else:
            output_stem = dataset_stem(pdf_path)
            output_path = RAG_DATA_PATH / f"{output_stem}_pages.jsonl"
        extract_pdf(pdf_path, output_path)


def extract_pdf(pdf_path: Path, output_path: Path) -> None:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    empty_pages = []
    pages_with_text = 0

    with pymupdf.open(pdf_path) as pdf, output_path.open(
        "w", encoding="utf-8"
    ) as output:
        page_count = len(pdf)
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            if not text:
                empty_pages.append(page_number)
                continue

            record = {
                "source": pdf_path.name,
                "page": page_number,
                "text": text,
            }
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            pages_with_text += 1

    print(f"PDF: {pdf_path.name}")
    print(f"PDF pages: {page_count}")
    print(f"Pages with extractable text: {pages_with_text}")
    print(f"Pages without text: {empty_pages}")
    print(f"Saved extracted pages to: {output_path}")


if __name__ == "__main__":
    main()