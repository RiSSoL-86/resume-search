from abc import ABC, abstractmethod


class BaseChunker(ABC):
    """Split a free-form experience description into indexable chunks."""

    @abstractmethod
    async def split(self, description: str) -> list[str]:
        """Return the chunks of a single description."""
        raise NotImplementedError
