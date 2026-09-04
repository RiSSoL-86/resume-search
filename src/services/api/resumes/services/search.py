from asyncio import gather
from typing import TYPE_CHECKING, final, override

from apps.common.services.base import BaseService
from services.api.resumes.schemas import (
    MatchedChunk,
    MatchedExperience,
    ResumeFiltersPayload,
    ResumeHit,
    ResumeSearchRequest,
    ResumeSearchResponse,
)
from services.enrichment import Enrichers
from services.search_engines import SearchEngines
from services.search_engines.schemas import QueryVectors

if TYPE_CHECKING:
    from services.enrichment.base import BaseEnricher
    from services.enrichment.schemas import ResumeFilters
    from services.search_engines.base import BaseSearchEngine
    from services.search_engines.schemas import (
        ExperienceMatch,
        ResumeDocument,
        SearchResult,
    )


@final
class ResumeSearchService(BaseService):
    """Rank resumes against a free-form vacancy description."""

    def __init__(self) -> None:
        """Pick the search engine and the enricher this service runs on."""
        self.engine: BaseSearchEngine = SearchEngines.open_search.get_engine()
        self.enricher: BaseEnricher = Enrichers.open_ai.get_enricher()

    @override
    async def execute(
        self,
        payload: ResumeSearchRequest,
    ) -> ResumeSearchResponse:
        """Return the candidates that best fit the requirements."""
        filters, result = await self.rank(payload=payload)
        return ResumeSearchResponse(
            total=result.total,
            filters=ResumeFiltersPayload.from_domain(filters=filters),
            items=[
                self._build_hit(resume=resume) for resume in result.resumes
            ],
        )

    async def rank(
        self,
        payload: ResumeSearchRequest,
    ) -> tuple[ResumeFilters, SearchResult]:
        """Return the ranked resumes and the criteria they were ranked by."""
        filters = await self.resolve_filters(payload=payload)
        vectors = await self._embed(filters=filters)
        result = await self.engine.search_resumes(
            filters=filters,
            vectors=vectors,
            weights=payload.weights,
            size=payload.size,
            offset=payload.offset,
        )
        return filters, result

    async def resolve_filters(
        self,
        payload: ResumeSearchRequest,
    ) -> ResumeFilters:
        """Return the criteria to search with."""
        # Already reviewed by hand, so the model is not asked again.
        brief = payload.brief()
        filters = payload.filters or await self.enricher.extract_filters(
            brief=brief,
        )

        # An empty query returns noise, so the vacancy itself stands in.
        if not filters.semantic_query.strip():
            filters.semantic_query = brief.vacancy.strip()
        if not filters.role_query.strip():
            filters.role_query = ", ".join(filters.professional_roles)
        return filters

    async def _embed(self, filters: ResumeFilters) -> QueryVectors:
        """Return the vectors the semantic clauses are matched with."""
        if not filters.role_query:
            return QueryVectors(
                description=await self.enricher.embed_query(
                    text=filters.semantic_query,
                ),
            )

        description, head = await gather(
            self.enricher.embed_query(text=filters.semantic_query),
            self.enricher.embed_query(text=filters.role_query),
        )
        return QueryVectors(description=description, head=head)

    @classmethod
    def _build_hit(cls, resume: ResumeDocument) -> ResumeHit:
        """Build one ranked candidate from an indexed resume."""
        source = resume.source
        area = source.get("area") or {}
        salary = source.get("salary") or {}
        total_experience = source.get("total_experience") or {}

        return ResumeHit(
            id=resume.id,
            score=resume.score,
            title=source.get("title"),
            alternate_url=source.get("alternate_url"),
            area=area.get("name"),
            age=source.get("age"),
            total_experience_months=total_experience.get("months"),
            salary_amount=salary.get("amount"),
            salary_currency=salary.get("currency"),
            skill_set=source.get("skill_set") or [],
            matched_experience=[
                cls._build_experience(match=match) for match in resume.matches
            ],
        )

    @staticmethod
    def _build_experience(match: ExperienceMatch) -> MatchedExperience:
        """Build the API view of one matched job."""
        return MatchedExperience(
            position=match.position,
            company=match.company,
            start=match.start,
            end=match.end,
            score=match.score,
            chunks=[
                MatchedChunk(text=chunk.text, score=chunk.score)
                for chunk in match.chunks
            ],
        )
