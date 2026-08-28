import json
from typing import Any, final, override

from services.indexing.constants import NOT_AN_OBJECT
from services.indexing.exceptions import UnreadableSourceError
from services.indexing.sources.base import BaseResumeSource
from services.indexing.sources.utils import limit_resumes


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
        return limit_resumes(resumes=resumes, errors=errors), errors
