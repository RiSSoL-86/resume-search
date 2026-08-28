import json
from abc import ABC, abstractmethod
from typing import IO, Any, final, override
from zipfile import BadZipFile, ZipFile, ZipInfo

from services.indexing.constants import (
    LARGE_RESUME,
    MACOS_DIRECTORY,
    MACOS_PREFIX,
    MAX_RESUME_BYTES,
    MAX_RESUMES,
    MEGABYTE,
    NOT_AN_OBJECT,
    TOO_MANY_RESUMES,
    ZIP_SIGNATURE,
)
from services.indexing.exceptions import UnreadableSourceError


def _is_macos_shadow(name: str) -> bool:
    """Report whether an entry is the shadow copy a mac zips alongside."""
    if name.startswith(MACOS_DIRECTORY):
        return True
    return name.rsplit("/", maxsplit=1)[-1].startswith(MACOS_PREFIX)


def _limit(
    resumes: list[dict[str, Any]],
    errors: list[str],
) -> list[dict[str, Any]]:
    """Cut an oversized upload down, saying so in the errors."""
    # A truncated upload has to say so, not look like a whole one.
    if len(resumes) > MAX_RESUMES:
        errors.append(TOO_MANY_RESUMES.format(len(resumes), MAX_RESUMES))
    return resumes[:MAX_RESUMES]


class BaseResumeSource(ABC):
    """The resume records an uploaded file carries."""

    def __init__(self, stream: IO[bytes]) -> None:
        """Take the uploaded file as an open binary stream."""
        self.stream = stream

    @abstractmethod
    def read(self) -> tuple[list[dict[str, Any]], list[str]]:
        """Return the records the file holds and what would not read."""
        raise NotImplementedError

    def count(self) -> int:
        """Return how many records the file holds."""
        resumes, _ = self.read()
        return len(resumes)


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
        return _limit(resumes=resumes, errors=errors), errors

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
            if _is_macos_shadow(name=info.filename):
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


@final
class JsonResumeSource(BaseResumeSource):
    """The resumes one JSON file carries, a list of them or a single one."""

    @override
    def read(self) -> tuple[list[dict[str, Any]], list[str]]:
        """Return the records the file holds and what would not read."""
        self.stream.seek(0)
        try:
            raw = json.loads(self.stream.read().decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise UnreadableSourceError(str(error)) from None

        errors: list[str] = []
        resumes: list[dict[str, Any]] = []
        records = raw if isinstance(raw, list) else [raw]
        for position, record in enumerate(records):
            if isinstance(record, dict):
                resumes.append(record)
            else:
                errors.append(NOT_AN_OBJECT.format(f"запись {position}"))
        return _limit(resumes=resumes, errors=errors), errors


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
