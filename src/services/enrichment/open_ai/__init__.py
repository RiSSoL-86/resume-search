from functools import lru_cache
from typing import TYPE_CHECKING, final

from django.conf import settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from services.enrichment.open_ai.constants import (
    EMBEDDING_BATCH_SIZE,
    LLM_SEED,
    LLM_TEMPERATURE,
)
from services.enrichment.open_ai.enricher import OpenAIEnricher

if TYPE_CHECKING:
    from services.enrichment.base import BaseEnricher

__all__ = ["OpenAIBackend"]


@final
class OpenAIBackend:
    """Give out the OpenAI pieces a service is to work through."""

    @classmethod
    @lru_cache(maxsize=1)
    def get_enricher(cls) -> BaseEnricher:
        """Return the enricher filters are extracted and embedded with."""
        llm = OpenAI(
            model=settings.OPENAI_LLM_MODEL,  # type: ignore[misc]
            api_key=settings.OPENAI_API_KEY,  # type: ignore[misc]
            temperature=LLM_TEMPERATURE,
            additional_kwargs={"seed": LLM_SEED},
        )
        # Must stay the model the index was built with.
        embed_model = OpenAIEmbedding(
            model=settings.OPENAI_EMBEDDING_MODEL,  # type: ignore[misc]
            api_key=settings.OPENAI_API_KEY,  # type: ignore[misc]
            dimensions=settings.OPENAI_EMBEDDING_DIMENSION,  # type: ignore[misc]
            embed_batch_size=EMBEDDING_BATCH_SIZE,
        )
        return OpenAIEnricher(llm=llm, embed_model=embed_model)
