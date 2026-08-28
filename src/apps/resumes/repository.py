from typing import TYPE_CHECKING, final
from uuid import UUID

from apps.common.repository import BaseRepository
from apps.resumes.models import IndexedResume, ResumeUpload, SearchPlan

if TYPE_CHECKING:
    from apps.resumes.choices import UploadStatus

REPORT_FIELDS = [
    "status",
    "indexed",
    "unchanged",
    "skipped",
    "chunks",
    "sources",
    "errors",
]


@final
class ResumeUploadRepository(BaseRepository[ResumeUpload, UUID]):
    """Read and write uploaded files of resumes."""

    model = ResumeUpload

    async def set_status(
        self,
        upload: ResumeUpload,
        status: UploadStatus,
    ) -> None:
        """Move an upload to the stage it has reached."""
        upload.status = status
        await self.save(instance=upload, fields=["status"])

    async def save_report(self, upload: ResumeUpload) -> None:
        """Store what the indexing run made of the upload."""
        await self.save(instance=upload, fields=REPORT_FIELDS)


@final
class SearchPlanRepository(BaseRepository[SearchPlan, UUID]):
    """Read and write the searches whose ranking can still be re-weighted."""

    model = SearchPlan

    async def remember_weights(
        self,
        plan: SearchPlan,
        weights: dict[str, float],
    ) -> None:
        """Store where the recruiter left the sliders."""
        plan.weights = weights
        await self.save(instance=plan, fields=["weights", "updated_timestamp"])


@final
class IndexedResumeRepository(BaseRepository[IndexedResume, UUID]):
    """Read and write the fingerprints of the resumes already indexed."""

    model = IndexedResume

    async def fingerprints(self, resume_ids: list[str]) -> dict[str, str]:
        """Return the stored fingerprint of every resume already indexed."""
        rows = self.model.objects.filter(
            resume_id__in=resume_ids,
        ).values_list("resume_id", "fingerprint")
        return {
            resume_id: fingerprint async for resume_id, fingerprint in rows
        }

    async def remember(self, resumes: list[IndexedResume]) -> None:
        """Store a fingerprint per resume, replacing the ones stored before."""
        await self.model.objects.abulk_create(
            resumes,
            update_conflicts=True,
            update_fields=["source", "fingerprint", "updated_timestamp"],
            unique_fields=["resume_id"],
        )
