from typing import Any, final

from pydantic import BaseModel, Field

Clause = dict[str, Any]

# Past this a single slider decides the ranking on its own.
MAX_WEIGHT = 3.0


@final
class QueryVectors(BaseModel):
    """The vectors one search is run with."""

    description: list[float] = Field(default_factory=list)
    head: list[float] = Field(default_factory=list)


@final
class SearchWeights(BaseModel):
    """What each part of the ranking counts for against the others."""

    # The first three are shares of the score, the last two are boosts.
    lexical: float = Field(
        default=0.2,
        ge=0.0,
        le=MAX_WEIGHT,
        description="How much the wording of the resume itself decides.",
    )
    semantic: float = Field(
        default=0.3,
        ge=0.0,
        le=MAX_WEIGHT,
        description="How much the meaning of the described work decides.",
    )
    technology: float = Field(
        default=0.5,
        ge=0.0,
        le=MAX_WEIGHT,
        description="How much the named technologies decide.",
    )
    role: float = Field(
        default=1.5,
        ge=0.0,
        le=MAX_WEIGHT,
        description="How much the years spent in the wanted role are worth.",
    )
    preference: float = Field(
        default=0.5,
        ge=0.0,
        le=MAX_WEIGHT,
        description="How much city, format, education and the like are worth.",
    )


@final
class DescriptionChunk(BaseModel):
    """A fragment of an experience description, ready to be stored."""

    order: int
    text: str
    vector: list[float] = Field(default_factory=list)


@final
class PreparedResume(BaseModel):
    """A resume the pipeline has chunked and embedded, awaiting storage."""

    # Both mappings are keyed by a position in experience.
    document: dict[str, Any] = Field(default_factory=dict)
    chunks: dict[int, list[DescriptionChunk]] = Field(default_factory=dict)
    heads: dict[int, list[float]] = Field(default_factory=dict)

    @property
    def id(self) -> str:
        """Return the identifier the resume is stored under."""
        return str(self.document["id"])


@final
class StoreOutcome(BaseModel):
    """What one write to the search engine managed to store."""

    stored: int = 0
    failed: set[str] = Field(default_factory=set)
    errors: list[str] = Field(default_factory=list)


@final
class SearchColumn(BaseModel):
    """One criterion of the ranking and the query scoring it."""

    key: str
    query: Clause

    # Whether the query returns only the resumes that answer it.
    from_zero: bool = False


@final
class ColumnScores(BaseModel):
    """What one criterion scored each resume it returned."""

    key: str
    scores: dict[str, float] = Field(default_factory=dict)
    from_zero: bool = False

    def normalized(self) -> dict[str, float]:
        """Return the scores brought onto a scale of nought to one."""
        # BM25 and cosine scales have nothing in common.
        if not self.scores:
            return {}

        highest = max(self.scores.values())
        lowest = 0.0 if self.from_zero else min(self.scores.values())
        spread = highest - lowest
        if not spread:
            return dict.fromkeys(self.scores, 1.0)

        return {
            resume_id: (score - lowest) / spread
            for resume_id, score in self.scores.items()
        }


@final
class PoolCandidate(BaseModel):
    """One candidate of the pool, scored on every criterion."""

    id: str
    scores: dict[str, float] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)

    def weighted(self, weights: SearchWeights) -> float:
        """Return the one score the criteria add up to at these weights."""
        return sum(
            getattr(weights, key, 0.0) * score
            for key, score in self.scores.items()
        )


@final
class ScoreMatrix(BaseModel):
    """The pool scored per criterion, so weights alone decide the order."""

    columns: list[str] = Field(default_factory=list)
    candidates: list[PoolCandidate] = Field(default_factory=list)

    def ranked(
        self, weights: SearchWeights
    ) -> list[tuple[PoolCandidate, float]]:
        """Return the pool ordered by the weighted sum, best first."""
        # Divided by what was on offer, so a moved slider keeps the scale.
        total = sum(getattr(weights, key, 0.0) for key in self.columns) or 1.0

        scored = [
            (candidate, candidate.weighted(weights=weights) / total)
            for candidate in self.candidates
        ]
        return sorted(scored, key=lambda entry: entry[1], reverse=True)


@final
class ChunkMatch(BaseModel):
    """A fragment of an experience description that matched."""

    text: str
    score: float


@final
class ExperienceMatch(BaseModel):
    """The job whose description matched the query."""

    position: str | None = None
    company: str | None = None
    start: str | None = None
    end: str | None = None
    score: float
    chunks: list[ChunkMatch] = Field(default_factory=list)


@final
class ResumeDocument(BaseModel):
    """One ranked resume together with the reason it ranked there."""

    id: str
    score: float
    source: dict[str, Any] = Field(default_factory=dict)
    matches: list[ExperienceMatch] = Field(default_factory=list)


@final
class SearchResult(BaseModel):
    """One page of ranked resumes, and the pool it was ranked out of."""

    total: int
    resumes: list[ResumeDocument] = Field(default_factory=list)
    matrix: ScoreMatrix = Field(
        default_factory=ScoreMatrix,
        description=(
            "Every candidate the criteria reached, scored per criterion. "
            "Re-weighting this is what a moved slider costs."
        ),
    )
