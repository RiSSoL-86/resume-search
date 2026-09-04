from typing import TYPE_CHECKING, final

from services.search_engines.schemas import PoolCandidate, ScoreMatrix

if TYPE_CHECKING:
    from services.search_engines.schemas import ColumnScores

# Enough to sort by, and four times shorter on the wire than a float.
SCORE_PRECISION = 4


@final
class ScoreFusion:
    """Bring the criteria onto one scale and lay them out as a matrix."""

    def __init__(self, columns: list[ColumnScores]) -> None:
        """Take what each criterion scored the resumes it returned."""
        self.columns = columns

    def matrix(self) -> ScoreMatrix:
        """Return every candidate any criterion returned, scored on all."""
        # Normalised once over the fixed pool and never again: a weight
        # moved afterwards must not change what a candidate is worth here.
        normalized = {
            column.key: column.normalized() for column in self.columns
        }
        pool = {
            resume_id for scores in normalized.values() for resume_id in scores
        }

        return ScoreMatrix(
            columns=[column.key for column in self.columns],
            candidates=[
                PoolCandidate(
                    id=resume_id,
                    scores={
                        key: round(scores.get(resume_id, 0.0), SCORE_PRECISION)
                        for key, scores in normalized.items()
                    },
                )
                for resume_id in pool
            ],
        )
