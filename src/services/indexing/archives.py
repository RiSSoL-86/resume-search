import json
from typing import IO, Any, final
from zipfile import ZipFile, ZipInfo

from services.indexing.constants import (
    LARGE_RESUME,
    MAX_RESUME_BYTES,
    MAX_RESUMES,
    MEGABYTE,
    NOT_AN_OBJECT,
    TOO_MANY_RESUMES,
)


@final
class ResumeArchive:
    """The resume files a zip archive carries."""

    def __init__(self, source: IO[bytes]) -> None:
        """Take the archive as an open binary stream."""
        self.source = source

    def count(self) -> int:
        """Return how many resume files the archive holds."""
        # Reads the directory of the archive only, not the files themselves.
        with ZipFile(self.source) as bundle:
            return len(self._entries(bundle=bundle, errors=[]))

    def read(self) -> tuple[list[dict[str, Any]], list[str]]:
        """Return the resumes the archive holds and what would not read."""
        resumes: list[dict[str, Any]] = []
        errors: list[str] = []
        with ZipFile(self.source) as bundle:
            for entry in self._entries(bundle=bundle, errors=errors):
                self._read_entry(
                    bundle=bundle,
                    entry=entry,
                    resumes=resumes,
                    errors=errors,
                )
        return resumes, errors

    @staticmethod
    def _entries(bundle: ZipFile, errors: list[str]) -> list[ZipInfo]:
        """Return the resume files of an archive, oversized ones dropped."""
        entries = []
        for info in bundle.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".json"):
                continue
            if info.file_size > MAX_RESUME_BYTES:
                errors.append(
                    LARGE_RESUME.format(
                        info.filename,
                        MAX_RESUME_BYTES // MEGABYTE,
                    ),
                )
                continue
            entries.append(info)

        # A truncated upload has to say so, not look like a whole one.
        if len(entries) > MAX_RESUMES:
            errors.append(TOO_MANY_RESUMES.format(len(entries), MAX_RESUMES))
        return entries[:MAX_RESUMES]

    @staticmethod
    def _read_entry(
        bundle: ZipFile,
        entry: ZipInfo,
        resumes: list[dict[str, Any]],
        errors: list[str],
    ) -> None:
        """Decode one archived file into the resumes read so far."""
        try:
            raw = json.loads(bundle.read(entry).decode("utf-8"))
        except (OSError, ValueError) as error:
            errors.append(f"{entry.filename}: {error}")
            return

        if not isinstance(raw, dict):
            errors.append(NOT_AN_OBJECT.format(entry.filename))
            return
        resumes.append(raw)
