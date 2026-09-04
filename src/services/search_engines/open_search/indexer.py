import json
import logging
from collections.abc import Iterable, Iterator
from copy import deepcopy
from typing import TYPE_CHECKING, Any, final, override

from opensearchpy.helpers import async_bulk

from services.search_engines.base import BaseResumeIndex
from services.search_engines.open_search.constants import FULL_RESUMES_INDEX
from services.search_engines.schemas import StoreOutcome

if TYPE_CHECKING:
    from opensearchpy import AsyncOpenSearch

    from services.search_engines.schemas import PreparedResume

logger = logging.getLogger(__name__)


@final
class OpenSearchResumeIndex(BaseResumeIndex):
    """Store prepared resumes in the OpenSearch index the engine queries."""

    def __init__(
        self,
        client: AsyncOpenSearch,
        mapping: dict[str, Any],
    ) -> None:
        """Take the client and the mapping the index is created with."""
        self.client = client
        self.mapping = mapping

    @override
    async def prepare(self) -> None:
        """Create the index if the cluster is still empty."""
        if await self.client.indices.exists(index=FULL_RESUMES_INDEX):
            return

        logger.info("Creating the %s index", FULL_RESUMES_INDEX)
        await self.client.indices.create(
            index=FULL_RESUMES_INDEX,
            body=self.mapping,
        )

    @override
    async def store(self, resumes: list[PreparedResume]) -> StoreOutcome:
        """Send one batch to the index, reporting what would not go in."""
        documents = [self._build_document(resume=resume) for resume in resumes]
        _, errors = await async_bulk(
            client=self.client,
            actions=self._actions(documents=documents),
            raise_on_error=False,
        )
        # async_bulk returns a list unless stats_only is set.
        failures = errors if isinstance(errors, list) else []

        outcome = StoreOutcome(stored=len(documents) - len(failures))
        for failure in failures:
            outcome.errors.append(json.dumps(failure, ensure_ascii=False))
            logger.error("Bulk failure: %s", failure)
            for action in failure.values():
                outcome.failed.add(str(action.get("_id")))
        return outcome

    @override
    async def commit(self) -> None:
        """Make everything stored so far visible to the search."""
        await self.client.indices.refresh(index=FULL_RESUMES_INDEX)

    @staticmethod
    def _build_document(resume: PreparedResume) -> dict[str, Any]:
        """Lay a prepared resume out the way this index stores it."""
        document = deepcopy(resume.document)

        for position, entry in enumerate(document.get("experience") or []):
            if not isinstance(entry, dict):
                continue
            entry["description_chunks"] = [
                chunk.model_dump() for chunk in resume.chunks.get(position, [])
            ]
            head_vector = resume.heads.get(position)
            if head_vector:
                entry["head_vector"] = head_vector

        return document

    @staticmethod
    def _actions(
        documents: Iterable[dict[str, Any]],
    ) -> Iterator[dict[str, Any]]:
        """Turn documents into OpenSearch bulk actions."""
        # The resume id is the document id, so a re-upload updates.
        for document in documents:
            yield {
                "_index": FULL_RESUMES_INDEX,
                "_id": document["id"],
                "_source": document,
            }
