from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from apps.resumes.choices import ResumeSource


class BaseResumeParser(ABC):
    """Turn the records of one system into the document the index expects."""

    source: ClassVar[ResumeSource]

    @abstractmethod
    def matches(self, raw: dict[str, Any]) -> bool:
        """Report whether the record comes from this system."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Return the record in the shape every indexed resume has."""
        raise NotImplementedError
