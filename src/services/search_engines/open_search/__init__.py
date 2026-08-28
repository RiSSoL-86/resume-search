from functools import lru_cache
from typing import TYPE_CHECKING, final

from django.conf import settings
from opensearchpy import AsyncOpenSearch

from services.search_engines.open_search.constants import MAX_RETRIES, TIMEOUT
from services.search_engines.open_search.engine import OpenSearchEngine
from services.search_engines.open_search.indexer import OpenSearchResumeIndex
from services.search_engines.open_search.mappings import (
    load_full_resumes_mapping,
)

if TYPE_CHECKING:
    from services.search_engines.base import BaseResumeIndex, BaseSearchEngine

__all__ = ["OpenSearchBackend"]


@final
class OpenSearchBackend:
    """Give out the OpenSearch pieces a service is to work through."""

    @classmethod
    @lru_cache(maxsize=1)
    def get_client(cls) -> AsyncOpenSearch:
        """Return the connection pool the engine and the index share."""
        return AsyncOpenSearch(
            hosts=settings.OPENSEARCH_HOSTS,  # type: ignore[misc]
            timeout=TIMEOUT,
            max_retries=MAX_RETRIES,
            retry_on_timeout=True,
        )

    @classmethod
    @lru_cache(maxsize=1)
    def get_engine(cls) -> BaseSearchEngine:
        """Return the engine resumes are searched with."""
        return OpenSearchEngine(client=cls.get_client())

    @classmethod
    @lru_cache(maxsize=1)
    def get_index(cls) -> BaseResumeIndex:
        """Return the index resumes are stored in."""
        return OpenSearchResumeIndex(
            client=cls.get_client(),
            mapping=load_full_resumes_mapping(
                dimension=settings.OPENAI_EMBEDDING_DIMENSION,  # type: ignore[misc]
            ),
        )
