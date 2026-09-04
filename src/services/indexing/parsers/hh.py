from typing import Any, ClassVar, final, override

from apps.resumes.choices import ResumeSource
from services.indexing.parsers.base import BaseResumeParser


@final
class HHResumeParser(BaseResumeParser):
    """Read the resumes an hh.ru export carries."""

    source: ClassVar[ResumeSource] = ResumeSource.HH

    @override
    def matches(self, raw: dict[str, Any]) -> bool:
        """Report whether the record is an hh.ru resume."""
        return bool(raw.get("id")) and isinstance(raw.get("experience"), list)

    @override
    def parse(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Return the record as it is, since the index is shaped after it."""
        return {**raw, "id": str(raw["id"]), "source": self.source.value}
