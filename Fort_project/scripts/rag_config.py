from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DOCUMENTS_PATH = PROJECT_ROOT / "data" / "raw" / "documents"
RAG_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "rag"
INDEXES_PATH = PROJECT_ROOT / "data" / "indexes"

PDF_DATASETS = {
    "purohit": {"filename": "Purohit-13.pdf", "stem": "purohit"},
    "imperial-gazetteer": {
        "filename": "The_Imperial_gazetteer.pdf",
        "stem": "the_imperial_gazetteer",
    },
    "battle-of-sinhagad": {
        "filename": "Battle of Sinhagad - Wikipedia.pdf",
        "stem": "battle_of_sinhagad_wikipedia",
    },
    "gipe": {"filename": "GIPE-017854.pdf", "stem": "gipe_017854"},
    "maharashtra-tourism": {
        "filename": "Maharashtra_Torism_fort.pdf",
        "stem": "maharashtra_torism_fort",
    },
    "pune-gazetteer": {
        "filename": "Pune_district_gazzeter.pdf",
        "stem": "pune_district_gazzeter",
    },
    "sinhagad": {
        "filename": "Sinhagad - Wikipedia.pdf",
        "stem": "sinhagad_wikipedia",
    },
}

PDF_CHOICES = (*PDF_DATASETS, "all")


def selected_datasets(pdf: str) -> list[tuple[str, dict[str, str]]]:
    if pdf == "all":
        return list(PDF_DATASETS.items())
    return [(pdf, PDF_DATASETS[pdf])]
