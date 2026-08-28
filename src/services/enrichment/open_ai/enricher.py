from hashlib import sha256
from typing import TYPE_CHECKING, final, override

from django.core.cache import cache

from services.enrichment.base import BaseEnricher
from services.enrichment.open_ai.constants import (
    FILTERS_CACHE_PREFIX,
    FILTERS_CACHE_TIMEOUT,
)
from services.enrichment.open_ai.prompts import EXTRACT_FILTERS_PROMPT
from services.enrichment.schemas import ResumeFilters

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding
    from llama_index.core.llms import LLM

    from services.enrichment.schemas import VacancyBrief


@final
class OpenAIEnricher(BaseEnricher):
    """Extract filters and embed queries with the OpenAI models."""

    def __init__(self, llm: LLM, embed_model: BaseEmbedding) -> None:
        """Take the models, already configured."""
        self.llm = llm
        self.embed_model = embed_model

    @override
    async def extract_filters(self, brief: VacancyBrief) -> ResumeFilters:
        """Return the structured criteria the three texts state."""
        text = brief.as_text()
        key = self._cache_key(requirements=text)

        stored = await cache.aget(key)
        if stored is not None:
            return ResumeFilters.model_validate_json(stored)

        filters: ResumeFilters = await self.llm.astructured_predict(
            output_cls=ResumeFilters,
            prompt=EXTRACT_FILTERS_PROMPT,
            requirements=text,
        )
        await cache.aset(key, filters.model_dump_json(), FILTERS_CACHE_TIMEOUT)
        return filters

    def _cache_key(self, requirements: str) -> str:
        """Return the key the criteria of these requirements are kept under."""
        # A new model, prompt or schema must leave the old criteria behind.
        parts = "\n".join(
            (
                self.llm.metadata.model_name,
                EXTRACT_FILTERS_PROMPT.template,
                str(ResumeFilters.model_json_schema()),
                requirements,
            ),
        )
        return f"{FILTERS_CACHE_PREFIX}:{sha256(parts.encode()).hexdigest()}"

    @override
    async def embed_query(self, text: str) -> list[float]:
        """Return the vector of a search query."""
        vector: list[float] = await self.embed_model.aget_query_embedding(
            query=text,
        )
        return vector

    @override
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per indexed text, in the order given."""
        if not texts:
            return []

        vectors: list[
            list[float]
        ] = await self.embed_model.aget_text_embedding_batch(texts=texts)
        return vectors
