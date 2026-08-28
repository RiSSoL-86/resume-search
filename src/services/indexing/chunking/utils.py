from services.indexing.constants import CHUNK_MIN_CHARS, CHUNK_SIZE


def merge_short(chunks: list[str]) -> list[str]:
    """Fold chunks below the minimum length into their neighbour."""
    # A lone header embeds poorly, but gives the next chunk context.
    merged: list[str] = []
    for chunk in chunks:
        text = chunk.strip()
        if not text:
            continue
        if (
            merged
            and len(merged[-1]) < CHUNK_MIN_CHARS
            and len(merged[-1]) + len(text) <= CHUNK_SIZE
        ):
            merged[-1] = f"{merged[-1]}\n{text}"
        else:
            merged.append(text)
    return merged
