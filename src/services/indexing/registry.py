import json
from hashlib import sha256
from typing import Any, final

from apps.resumes.models import IndexedResume
from apps.resumes.repository import IndexedResumeRepository


@final
class IndexedResumeRegistry:
    """Remember which resumes were embedded, so none is embedded twice."""

    def __init__(self) -> None:
        """Take the repository the fingerprints are kept in."""
        self.repository = IndexedResumeRepository()

    @staticmethod
    def fingerprint(document: dict[str, Any]) -> str:
        """Return the hash a resume is recognised as unchanged by."""
        payload = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    async def select_changed(
        self,
        documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return the documents that differ from what was indexed before."""
        # Embedding is what an upload spends its hour on; this skips it.
        stored = await self.repository.fingerprints(
            resume_ids=[document["id"] for document in documents],
        )
        return [
            document
            for document in documents
            if stored.get(document["id"])
            != self.fingerprint(document=document)
        ]

    async def remember(self, documents: list[dict[str, Any]]) -> None:
        """Write down that these resumes are in the index as they are now."""
        await self.repository.remember(
            resumes=[
                IndexedResume(
                    resume_id=document["id"],
                    source=document["source"],
                    fingerprint=self.fingerprint(document=document),
                )
                for document in documents
            ],
        )
