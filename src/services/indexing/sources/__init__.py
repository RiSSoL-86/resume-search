from typing import IO, TYPE_CHECKING, final

from services.indexing.constants import ZIP_SIGNATURE
from services.indexing.sources.json_file import JsonResumeSource
from services.indexing.sources.zip_archive import ZipResumeSource

if TYPE_CHECKING:
    from services.indexing.sources.base import BaseResumeSource

__all__ = ["ResumeSources"]


@final
class ResumeSources:
    """Give out the source an uploaded file is read with."""

    @staticmethod
    def get_source(stream: IO[bytes]) -> BaseResumeSource:
        """Return the source that matches what the file starts with."""
        stream.seek(0)
        signature = stream.read(len(ZIP_SIGNATURE))
        stream.seek(0)
        if signature == ZIP_SIGNATURE:
            return ZipResumeSource(stream=stream)
        return JsonResumeSource(stream=stream)
