from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.search_engines.schemas import PreparedResume


def build_document(resume: PreparedResume) -> dict[str, Any]:
    """Lay a prepared resume out the way this index stores it."""
    document = deepcopy(resume.document)

    for position, entry in enumerate(document.get("experience") or []):
        if not isinstance(entry, dict):
            continue
        entry["description_chunks"] = [
            chunk.model_dump() for chunk in resume.chunks.get(position, [])
        ]
        head_vector = resume.heads.get(position)
        if head_vector:
            entry["head_vector"] = head_vector

    return document
