from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.enrichment.schemas import ResumeFilters, VacancyBrief


class BaseEnricher(ABC):
    """Turn a free-form vacancy description into searchable input."""

    @abstractmethod
    async def extract_filters(self, brief: VacancyBrief) -> ResumeFilters:
        """Return the structured criteria the three texts state."""
        raise NotImplementedError

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Return the vector of a search query."""
        raise NotImplementedError

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per indexed text, in the order given."""
        raise NotImplementedError
