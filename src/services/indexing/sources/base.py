from abc import ABC, abstractmethod
from typing import IO, Any


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
