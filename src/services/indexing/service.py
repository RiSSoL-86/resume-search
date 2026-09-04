import logging
from typing import TYPE_CHECKING, final, override

from apps.common.services.base import BaseService
from apps.resumes.choices import UploadStatus
from apps.resumes.repository import ResumeUploadRepository
from services.enrichment import Enrichers
from services.indexing.chunking.structural import StructuralChunker
from services.indexing.directories.companies import CompanyDirectory
from services.indexing.parsers.hh import HHResumeParser
from services.indexing.parsers.humart import HumartResumeParser
from services.indexing.parsers.normalizer import ResumeNormalizer
from services.indexing.pipeline import ResumeIndexingPipeline
from services.indexing.registry import IndexedResumeRegistry
from services.indexing.sources import ResumeSources
from services.search_engines import SearchEngines

if TYPE_CHECKING:
    from uuid import UUID

    from apps.resumes.models import ResumeUpload

logger = logging.getLogger(__name__)


@final
class ResumeUploadIndexingService(BaseService):
    """Index the resumes one upload carries."""

    def __init__(self) -> None:
        """Wire up everything an upload is indexed with."""
        self.repository = ResumeUploadRepository()
        self.pipeline = ResumeIndexingPipeline(
            index=SearchEngines.open_search.get_index(),
            normalizer=ResumeNormalizer(
                parsers=(
                    HHResumeParser(),
                    HumartResumeParser(directory=CompanyDirectory()),
                ),
            ),
            registry=IndexedResumeRegistry(),
            chunker=StructuralChunker(),
            enricher=Enrichers.open_ai.get_enricher(),
        )

    @override
    async def execute(self, upload_id: UUID) -> None:
        """Read the stored file and put every resume into the index."""
        upload = await self.repository.get(primary_key=upload_id)
        if upload is None:
            logger.warning("Upload %s is gone, nothing to index", upload_id)
            return

        logger.info("Upload %s started: %s", upload.id, upload.file.name)
        await self.repository.set_status(
            upload=upload,
            status=UploadStatus.RUNNING,
        )

        try:
            await self._index(upload=upload)
        except Exception:
            logger.exception("Upload %s failed", upload.id)
            upload.status = UploadStatus.FAILED
            await self.repository.save_report(upload=upload)
            raise

    async def _index(self, upload: ResumeUpload) -> None:
        """Index the resumes and write down what the run did."""
        with upload.file.open(mode="rb") as stream:
            resumes, errors = ResumeSources.get_source(stream=stream).read()
        logger.info("Upload %s holds %s records", upload.id, len(resumes))

        report = await self.pipeline.index_resumes(resumes=resumes)

        upload.status = UploadStatus.INDEXED
        upload.indexed = report.indexed
        upload.unchanged = report.unchanged
        upload.skipped = report.skipped
        upload.chunks = report.chunks
        upload.sources = report.sources
        upload.errors = errors + report.errors
        await self.repository.save_report(upload=upload)
        logger.info(
            "Upload %s finished: indexed %s, unchanged %s, skipped %s",
            upload.id,
            report.indexed,
            report.unchanged,
            report.skipped,
        )
