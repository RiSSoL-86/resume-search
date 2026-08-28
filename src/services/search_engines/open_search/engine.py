from asyncio import gather
from typing import TYPE_CHECKING, Any, final, override

from services.search_engines.base import BaseSearchEngine
from services.search_engines.open_search.constants import (
    FULL_RESUMES_INDEX,
    POOL_DEPTH,
)
from services.search_engines.open_search.fusion import ScoreFusion
from services.search_engines.open_search.queries import ResumeQueryBuilder
from services.search_engines.schemas import (
    ChunkMatch,
    ColumnScores,
    ExperienceMatch,
    ResumeDocument,
    SearchResult,
)

if TYPE_CHECKING:
    from opensearchpy import AsyncOpenSearch

    from services.enrichment.schemas import ResumeFilters
    from services.search_engines.schemas import (
        QueryVectors,
        ScoreMatrix,
        SearchWeights,
    )


@final
class OpenSearchEngine(BaseSearchEngine):
    """Query the resume index and return ranked resumes."""

    def __init__(self, client: AsyncOpenSearch) -> None:
        """Take the client and build the query builder."""
        self.client = client
        self.queries = ResumeQueryBuilder()

    @override
    async def search_resumes(
        self,
        filters: ResumeFilters,
        vectors: QueryVectors,
        weights: SearchWeights,
        size: int,
        offset: int,
    ) -> SearchResult:
        """Return one page of resumes ranked against the criteria."""
        columns = self.queries.build_columns(filters=filters, vectors=vectors)
        responses = await gather(
            *(
                self.client.search(
                    index=FULL_RESUMES_INDEX,
                    body=self.queries.build_column_body(
                        filters=filters,
                        query=column.query,
                        size=POOL_DEPTH,
                    ),
                )
                for column in columns
            ),
        )

        matrix = ScoreFusion(
            columns=[
                ColumnScores(
                    key=column.key,
                    scores=self._scores(response=response),
                    from_zero=column.from_zero,
                )
                for column, response in zip(columns, responses, strict=True)
            ],
        ).matrix()

        ranked = matrix.ranked(weights=weights)
        matrix.candidates = [candidate for candidate, _ in ranked]
        await self._fill_brief(matrix=matrix)

        page = ranked[offset : offset + size]
        sources, matches = await self._fetch_documents(
            filters=filters,
            vectors=vectors,
            resume_ids=[candidate.id for candidate, _ in page],
        )

        # The page keeps the order the weighted scores ranked it in.
        return SearchResult(
            total=self._total(responses=responses),
            matrix=matrix,
            resumes=[
                ResumeDocument(
                    id=candidate.id,
                    score=score,
                    source=sources.get(candidate.id, {}),
                    matches=matches.get(candidate.id, []),
                )
                for candidate, score in page
            ],
        )

    async def _fill_brief(self, matrix: ScoreMatrix) -> None:
        """Give every candidate of the pool the little the list shows."""
        resume_ids = [candidate.id for candidate in matrix.candidates]
        if not resume_ids:
            return

        response = await self.client.search(
            index=FULL_RESUMES_INDEX,
            body=self.queries.build_brief_body(resume_ids=resume_ids),
        )
        brief = {
            hit["_id"]: hit.get("_source") or {}
            for hit in response["hits"]["hits"]
        }
        for candidate in matrix.candidates:
            candidate.source = brief.get(candidate.id, {})

    @staticmethod
    def _total(responses: list[dict[str, Any]]) -> int:
        """Return how many resumes answered the criteria at all."""
        # Ranking stops at the pool depth; the count shown does not.
        return max(
            (response["hits"]["total"]["value"] for response in responses),
            default=0,
        )

    @staticmethod
    def _scores(response: dict[str, Any]) -> dict[str, float]:
        """Return what one half scored each resume it matched."""
        return {
            hit["_id"]: hit.get("_score") or 0.0
            for hit in response["hits"]["hits"]
        }

    @override
    async def close(self) -> None:
        """Release the underlying connections."""
        await self.client.close()

    async def _fetch_documents(
        self,
        filters: ResumeFilters,
        vectors: QueryVectors,
        resume_ids: list[str],
    ) -> tuple[
        dict[str, dict[str, Any]],
        dict[str, list[ExperienceMatch]],
    ]:
        """Return the body and the matching jobs of each given resume."""
        if not resume_ids:
            return {}, {}

        response = await self.client.search(
            index=FULL_RESUMES_INDEX,
            body=self.queries.build_matches_body(
                filters=filters,
                vectors=vectors,
                resume_ids=resume_ids,
            ),
        )

        sources: dict[str, dict[str, Any]] = {}
        matches: dict[str, list[ExperienceMatch]] = {}
        for hit in response["hits"]["hits"]:
            sources[hit["_id"]] = hit.get("_source") or {}
            inner = hit.get("inner_hits", {}).get("experience", {})
            matches[hit["_id"]] = [
                self._parse_experience(entry=entry)
                for entry in inner.get("hits", {}).get("hits", [])
            ]
        return sources, matches

    @classmethod
    def _parse_experience(cls, entry: dict[str, Any]) -> ExperienceMatch:
        """Build one matched job from a nested inner hit."""
        source = entry.get("_source") or {}
        chunk_hits = (
            entry.get("inner_hits", {})
            .get("chunk", {})
            .get("hits", {})
            .get("hits", [])
        )
        return ExperienceMatch(
            position=source.get("position"),
            company=source.get("company"),
            start=source.get("start"),
            end=source.get("end"),
            score=entry.get("_score") or 0.0,
            chunks=[
                ChunkMatch(
                    text=(chunk.get("_source") or {}).get("text", ""),
                    score=chunk.get("_score") or 0.0,
                )
                for chunk in chunk_hits
            ],
        )
