from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.enrichment.schemas import ResumeFilters
    from services.search_engines.schemas import (
        PreparedResume,
        QueryVectors,
        SearchResult,
        SearchWeights,
        StoreOutcome,
    )


class BaseSearchEngine(ABC):
    """Rank indexed resumes against extracted criteria."""

    @abstractmethod
    async def search_resumes(
        self,
        filters: ResumeFilters,
        vectors: QueryVectors,
        weights: SearchWeights,
        size: int,
        offset: int,
    ) -> SearchResult:
        """Return one page of resumes ranked against the criteria."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Release the underlying connections."""
        raise NotImplementedError


class BaseResumeIndex(ABC):
    """Store prepared resumes where the search engine reads them from."""

    @abstractmethod
    async def prepare(self) -> None:
        """Make the store ready to be written to."""
        raise NotImplementedError

    @abstractmethod
    async def store(self, resumes: list[PreparedResume]) -> StoreOutcome:
        """Store the given resumes, replacing the ones already there."""
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        """Make everything stored so far visible to the search."""
        raise NotImplementedError
