import logging
from typing import TYPE_CHECKING, final, override

from apps.common.services.base import BaseService
from apps.resumes.models import ResumeUpload
from apps.resumes.repository import ResumeUploadRepository
from services.api.resumes.exceptions import (
    EmptyUploadError,
    UnreadableUploadError,
)
from services.api.resumes.schemas import ResumeUploadStatus
from services.celery_tasks.resume_uploads import index_resume_upload
from services.indexing.exceptions import UnreadableSourceError
from services.indexing.sources import ResumeSources

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


@final
class ResumeUploadService(BaseService):
    """Take a file of resumes in and queue it for indexing."""

    def __init__(self) -> None:
        """Take the repository the uploads are kept in."""
        self.repository = ResumeUploadRepository()

    @override
    async def execute(self, file: UploadedFile) -> ResumeUploadStatus:
        """Store the file and hand it over to a worker."""
        # Indexing takes minutes, but an unreadable file is caught at once.
        total = self._count(file=file)

        upload = await self.repository.create(ResumeUpload(file=file))
        logger.info(
            "Upload %s accepted: %s, %s records, queued for indexing",
            upload.id,
            file.name,
            total,
        )
        index_resume_upload.delay(str(upload.id))
        return ResumeUploadStatus.from_upload(upload=upload)

    @staticmethod
    def _count(file: UploadedFile) -> int:
        """Return how many records the file holds, refusing an empty one."""
        try:
            total = ResumeSources.get_source(stream=file).count()
        except UnreadableSourceError as error:
            logger.warning("Upload %s is unreadable: %s", file.name, error)
            raise UnreadableUploadError from None

        if not total:
            raise EmptyUploadError
        return total
