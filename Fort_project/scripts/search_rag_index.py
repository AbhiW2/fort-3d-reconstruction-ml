import argparse
import sys

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from rag_config import INDEXES_PATH, PDF_CHOICES, selected_datasets

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RESULT_COUNT = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find relevant passages in the local PDF FAISS indexes."
    )
    parser.add_argument(
        "--pdf",
        choices=PDF_CHOICES,
        default="purohit",
        help="PDF index to search, or all sources (default: purohit).",
    )
    parser.add_argument(
        "--query",
        help="Question to search for. If omitted, the script prompts for one.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=DEFAULT_RESULT_COUNT,
        help=f"Number of passages to return (default: {DEFAULT_RESULT_COUNT}).",
    )
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    if args.k < 1:
        raise ValueError("--k must be at least 1")

    query = (args.query or input("Enter a question about the PDF: ")).strip()
    if not query:
        raise ValueError("The search question cannot be empty")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    # The pickle is created by build_rag_index.py; only load an index you trust.
    results = []
    for dataset_name, dataset in selected_datasets(args.pdf):
        index_path = INDEXES_PATH / f"{dataset['stem']}_faiss"
        if not (index_path / "index.faiss").is_file() or not (
            index_path / "index.pkl"
        ).is_file():
            raise FileNotFoundError(
                f"FAISS index files not found in {index_path}. "
                f"Run scripts\\build_rag_index.py --pdf {dataset_name} first."
            )
        vector_store = FAISS.load_local(
            str(index_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        result_count = min(args.k, vector_store.index.ntotal)
        results.extend(
            vector_store.similarity_search_with_score(query, k=result_count)
        )
    results.sort(key=lambda result: result[1])
    results = results[: args.k]
    if not results:
        print("No matching passages found.")
        return

    for rank, (document, distance) in enumerate(results, start=1):
        print(f"\nResult {rank} (distance: {distance:.4f})")
        print(
            f"Source: {document.metadata['source']}, "
            f"page: {document.metadata['page']}, "
            f"chunk: {document.metadata['chunk_id']}"
        )
        print(document.page_content)

    print("\nLower distance means a closer vector match; it is not a confidence score.")


if __name__ == "__main__":
    main()
