import json
from typing import Any, final, override
from zipfile import BadZipFile, ZipFile, ZipInfo

from services.indexing.constants import (
    LARGE_RESUME,
    MAX_RESUME_BYTES,
    MEGABYTE,
)
from services.indexing.exceptions import UnreadableSourceError
from services.indexing.sources.base import BaseResumeSource
from services.indexing.sources.utils import is_macos_shadow, limit_resumes


@final
class ZipResumeSource(BaseResumeSource):
    """The resumes a zip archive of JSON files carries."""

    @override
    def read(self) -> tuple[list[dict[str, Any]], list[str]]:
        """Return the records the archive holds and what would not read."""
        resumes: list[dict[str, Any]] = []
        errors: list[str] = []
        with self._open() as bundle:
            for entry in self._entries(bundle=bundle, errors=errors):
                self._read_entry(
                    bundle=bundle,
                    entry=entry,
                    resumes=resumes,
                    errors=errors,
                )
        return limit_resumes(resumes=resumes, errors=errors), errors

    @override
    def count(self) -> int:
        """Return how many files the archive holds."""
        # Reads the directory of the archive only, not the files themselves.
        with self._open() as bundle:
            return len(self._entries(bundle=bundle, errors=[]))

    def _open(self) -> ZipFile:
        """Open the archive, refusing one that is not readable."""
        self.stream.seek(0)
        try:
            return ZipFile(self.stream)
        except BadZipFile as error:
            raise UnreadableSourceError(str(error)) from None

    @staticmethod
    def _entries(bundle: ZipFile, errors: list[str]) -> list[ZipInfo]:
        """Return the resume files of an archive, oversized ones dropped."""
        entries = []
        for info in bundle.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".json"):
                continue
            if is_macos_shadow(name=info.filename):
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
        return entries

    @staticmethod
    def _read_entry(
        bundle: ZipFile,
        entry: ZipInfo,
        resumes: list[dict[str, Any]],
        errors: list[str],
    ) -> None:
        """Decode one archived file into the records read so far."""
        try:
            raw = json.loads(bundle.read(entry).decode("utf-8"))
        except (OSError, ValueError) as error:
            errors.append(f"{entry.filename}: {error}")
            return

        # An export also carries manifests, and those are lists, not resumes.
        if isinstance(raw, dict):
            resumes.append(raw)
