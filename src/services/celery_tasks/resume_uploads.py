from uuid import UUID

from asgiref.sync import async_to_sync
from celery import shared_task

from services.indexing.service import ResumeUploadIndexingService


@shared_task(name="resume_uploads.index_resume_upload")
def index_resume_upload(upload_id: str) -> None:
    """Index one uploaded archive in its own worker."""
    service = ResumeUploadIndexingService()
    async_to_sync(awaitable=service.execute)(upload_id=UUID(upload_id))
