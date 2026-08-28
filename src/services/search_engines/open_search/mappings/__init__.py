import json
from pathlib import Path
from typing import Any

MAPPINGS_DIR = Path(__file__).resolve().parent


def load_full_resumes_mapping(dimension: int) -> dict[str, Any]:
    """Return the full-resume index definition for an embedding size."""
    path = MAPPINGS_DIR / "full_resumes.json"
    with path.open(encoding="utf-8") as mapping_file:
        mapping: dict[str, Any] = json.load(mapping_file)

    # The dimension written in the file is a default; the model decides it.
    chunks = mapping["mappings"]["properties"]["experience"]["properties"][
        "description_chunks"
    ]
    chunks["properties"]["vector"]["dimension"] = dimension
    return mapping
