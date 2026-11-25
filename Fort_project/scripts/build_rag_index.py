import argparse
import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from rag_config import INDEXES_PATH, PDF_CHOICES, RAG_DATA_PATH, selected_datasets

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embed PDF chunks and save a local FAISS index."
    )
    parser.add_argument(
        "--pdf",
        choices=PDF_CHOICES,
        default="purohit",
        help="PDF dataset to index, or all (default: purohit).",
    )
    return parser.parse_args()


def load_chunks(chunks_path: Path) -> list[Document]:
    if not chunks_path.is_file():
        raise FileNotFoundError(f"Chunk file not found: {chunks_path}")

    documents = []
    with chunks_path.open("r", encoding="utf-8") as chunks_file:
        for line_number, line in enumerate(chunks_file, start=1):
            try:
                record = json.loads(line)
                text = record["text"].strip()
                metadata = {
                    "chunk_id": record["chunk_id"],
                    "source": record["source"],
                    "page": record["page"],
                }
            except (json.JSONDecodeError, KeyError, AttributeError) as exc:
                raise ValueError(
                    f"Invalid chunk record on line {line_number}"
                ) from exc

            if text:
                documents.append(Document(page_content=text, metadata=metadata))

    if not documents:
        raise ValueError(f"No non-empty chunks found in {chunks_path}")
    return documents


def main() -> None:
    args = parse_args()
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    for _, dataset in selected_datasets(args.pdf):
        stem = dataset["stem"]
        chunks_path = RAG_DATA_PATH / f"{stem}_chunks.jsonl"
        index_path = INDEXES_PATH / f"{stem}_faiss"
        documents = load_chunks(chunks_path)
        vector_store = FAISS.from_documents(documents, embeddings)
        index_path.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(index_path))

        print(f"Embedded chunks: {len(documents)}")
        print(f"Embedding model: {EMBEDDING_MODEL}")
        print(f"Saved FAISS index to: {index_path}")


if __name__ == "__main__":
    main()
