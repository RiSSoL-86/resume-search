from typing import Any, final

from pydantic import BaseModel, Field


@final
class NormalizedResumes(BaseModel):
    """What one pile of raw records turned into."""

    documents: list[dict[str, Any]] = Field(default_factory=list)
    skipped: int = 0
    # How many documents each known source gave, for the logs.
    sources: dict[str, int] = Field(default_factory=dict)


@final
class IndexingReport(BaseModel):
    """What one indexing run did."""

    indexed: int = 0
    unchanged: int = 0
    skipped: int = 0
    chunks: int = 0
    sources: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
