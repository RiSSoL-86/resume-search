import logging
from datetime import date
from typing import TYPE_CHECKING, Any, final

from services.indexing.constants import BATCH_SIZE
from services.indexing.experience import ResumeExperience
from services.indexing.schemas import IndexingReport
from services.search_engines.schemas import DescriptionChunk, PreparedResume

if TYPE_CHECKING:
    from services.enrichment.base import BaseEnricher
    from services.indexing.chunking.base import BaseChunker
    from services.indexing.parsers.normalizer import ResumeNormalizer
    from services.indexing.registry import IndexedResumeRegistry
    from services.search_engines.base import BaseResumeIndex

logger = logging.getLogger(__name__)


@final
class ResumeIndexingPipeline:
    """Chunk, embed and store resumes, whatever engine stores them."""

    def __init__(
        self,
        index: BaseResumeIndex,
        normalizer: ResumeNormalizer,
        registry: IndexedResumeRegistry,
        chunker: BaseChunker,
        enricher: BaseEnricher,
    ) -> None:
        """Take every collaborator from the caller."""
        self.index = index
        self.normalizer = normalizer
        self.registry = registry
        self.chunker = chunker
        self.enricher = enricher

    async def index_resumes(
        self,
        resumes: list[dict[str, Any]],
    ) -> IndexingReport:
        """Index the given resumes, replacing the ones already stored."""
        report = IndexingReport()
        normalized = self.normalizer.normalize(resumes=resumes)
        report.skipped = normalized.skipped
        report.sources = normalized.sources

        batch = await self.registry.select_changed(
            documents=normalized.documents,
        )
        report.unchanged = len(normalized.documents) - len(batch)
        logger.info(
            "To embed: %s resumes, unchanged since the last run: %s",
            len(batch),
            report.unchanged,
        )
        if not batch:
            return report

        await self.index.prepare()
        batches = [
            batch[start : start + BATCH_SIZE]
            for start in range(0, len(batch), BATCH_SIZE)
        ]
        for number, part in enumerate(batches, start=1):
            await self._flush(
                batch=part,
                number=number,
                total=len(batches),
                report=report,
            )

        await self.index.commit()
        logger.info(
            "Indexed %s resumes in %s chunks, %s errors",
            report.indexed,
            report.chunks,
            len(report.errors),
        )
        return report

    async def _flush(
        self,
        batch: list[dict[str, Any]],
        number: int,
        total: int,
        report: IndexingReport,
    ) -> None:
        """Embed and store one batch of resumes."""
        logger.info(
            "Batch %s/%s: %s",
            number,
            total,
            "; ".join(
                f"{document['id']} {document.get('title') or '—'}"
                for document in batch
            ),
        )

        prepared = await self._prepare(batch=batch, report=report)
        if not prepared:
            return

        outcome = await self.index.store(resumes=prepared)
        report.indexed += outcome.stored
        report.errors.extend(outcome.errors)
        await self.registry.remember(
            documents=[
                document
                for document in batch
                if document["id"] not in outcome.failed
            ],
        )
        logger.info(
            "Batch %s/%s stored: %s resumes and %s chunks indexed so far",
            number,
            total,
            report.indexed,
            report.chunks,
        )

    async def _prepare(
        self,
        batch: list[dict[str, Any]],
        report: IndexingReport,
    ) -> list[PreparedResume]:
        """Chunk and embed a batch, returning resumes ready to be stored."""
        today = date.today()
        careers = [ResumeExperience(raw=raw, today=today) for raw in batch]

        texts: list[str] = []
        # Which resume and which job each text came from.
        owners: list[tuple[int, int]] = []

        per_resume: list[dict[int, list[str]]] = []
        for career in careers:
            chunks_by_position: dict[int, list[str]] = {}
            for position, description in career.descriptions():
                chunks = await self.chunker.split(description=description)
                if chunks:
                    chunks_by_position[position] = chunks
            per_resume.append(chunks_by_position)

        for resume_offset, chunks_by_position in enumerate(per_resume):
            for position, chunks in chunks_by_position.items():
                for chunk in chunks:
                    texts.append(chunk)
                    owners.append((resume_offset, position))

        chunk_count = len(texts)
        # Job titles ride along in the same request as the chunks.
        for resume_offset, career in enumerate(careers):
            for position, head in career.heads():
                texts.append(head)
                owners.append((resume_offset, position))

        logger.info(
            "Embedding %s texts: %s chunks and %s job titles",
            len(texts),
            chunk_count,
            len(texts) - chunk_count,
        )
        vectors = await self.enricher.embed_documents(texts=texts)
        if len(vectors) != len(texts):
            report.errors.append(
                f"Embedder returned {len(vectors)} vectors "
                f"for {len(texts)} texts",
            )
            logger.error(
                "Embedder returned %s vectors for %s texts, batch dropped",
                len(vectors),
                len(texts),
            )
            return []

        embedded: list[dict[int, list[DescriptionChunk]]] = [{} for _ in batch]
        for offset in range(chunk_count):
            resume_offset, position = owners[offset]
            entry = embedded[resume_offset].setdefault(position, [])
            entry.append(
                DescriptionChunk(
                    order=len(entry),
                    text=texts[offset],
                    vector=vectors[offset],
                ),
            )

        heads: list[dict[int, list[float]]] = [{} for _ in batch]
        for offset in range(chunk_count, len(texts)):
            resume_offset, position = owners[offset]
            heads[resume_offset][position] = vectors[offset]

        report.chunks += chunk_count
        return [
            PreparedResume(
                document=career.document(),
                chunks=embedded[resume_offset],
                heads=heads[resume_offset],
            )
            for resume_offset, career in enumerate(careers)
        ]
