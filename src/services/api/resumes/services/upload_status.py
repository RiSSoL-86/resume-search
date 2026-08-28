from typing import TYPE_CHECKING, final, override

from apps.common.services.base import BaseService
from apps.resumes.repository import ResumeUploadRepository
from services.api.resumes.exceptions import UnknownUploadError
from services.api.resumes.schemas import ResumeUploadStatus

if TYPE_CHECKING:
    from uuid import UUID


@final
class ResumeUploadStatusService(BaseService):
    """Report where one upload got to."""

    def __init__(self) -> None:
        """Take the repository the uploads are kept in."""
        self.repository = ResumeUploadRepository()

    @override
    async def execute(self, upload_id: UUID) -> ResumeUploadStatus:
        """Return the upload as it stands right now."""
        upload = await self.repository.get(primary_key=upload_id)
        if upload is None:
            raise UnknownUploadError
        return ResumeUploadStatus.from_upload(upload=upload)
