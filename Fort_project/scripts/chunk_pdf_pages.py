import argparse
import json

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_config import PDF_CHOICES, RAG_DATA_PATH, selected_datasets

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split extracted PDF pages into citation-preserving chunks."
    )
    parser.add_argument(
        "--pdf",
        choices=PDF_CHOICES,
        default="purohit",
        help="PDF dataset to chunk, or all (default: purohit).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if CHUNK_OVERLAP >= CHUNK_SIZE:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

    for _, dataset in selected_datasets(args.pdf):
        chunk_pdf(dataset["stem"])


def chunk_pdf(stem: str) -> None:
    input_path = RAG_DATA_PATH / f"{stem}_pages.jsonl"
    output_path = RAG_DATA_PATH / f"{stem}_chunks.jsonl"
    if not input_path.is_file():
        raise FileNotFoundError(f"Extracted pages file not found: {input_path}")

    documents = []
    with input_path.open("r", encoding="utf-8") as pages_file:
        for line_number, line in enumerate(pages_file, start=1):
            try:
                record = json.loads(line)
                text = record["text"].strip()
                source = record["source"]
                page = record["page"]
            except (json.JSONDecodeError, KeyError, AttributeError) as exc:
                raise ValueError(
                    f"Invalid extracted page record on line {line_number}"
                ) from exc

            if text:
                documents.append(
                    Document(
                        page_content=text,
                        metadata={"source": source, "page": page},
                    )
                )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)

    if not documents:
        raise ValueError(f"No non-empty pages found in {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as chunks_file:
        for chunk_id, chunk in enumerate(chunks):
            record = {
                "chunk_id": chunk_id,
                "source": chunk.metadata["source"],
                "page": chunk.metadata["page"],
                "text": chunk.page_content,
            }
            chunks_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Input pages with text: {len(documents)}")
    print(f"Created chunks: {len(chunks)}")
    print(f"Saved chunks to: {output_path}")


if __name__ == "__main__":
    main()
