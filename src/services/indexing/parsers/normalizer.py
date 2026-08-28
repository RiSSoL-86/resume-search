import logging
from typing import TYPE_CHECKING, Any, final

from services.indexing.schemas import NormalizedResumes

if TYPE_CHECKING:
    from collections.abc import Sequence

    from services.indexing.parsers.base import BaseResumeParser

logger = logging.getLogger(__name__)


@final
class ResumeNormalizer:
    """Bring the records of every known source to the one indexed shape."""

    def __init__(self, parsers: Sequence[BaseResumeParser]) -> None:
        """Take one parser per system resumes reach the index from."""
        self.parsers = parsers

    def normalize(self, resumes: list[dict[str, Any]]) -> NormalizedResumes:
        """Return one document per record any of the parsers recognises."""
        result = NormalizedResumes()
        # A re-uploaded file may name the same resume twice; the last wins.
        documents: dict[str, dict[str, Any]] = {}

        for raw in resumes:
            parser = self._parser_for(raw=raw)
            if parser is None:
                result.skipped += 1
                continue

            document = parser.parse(raw=raw)
            documents[document["id"]] = document
            source = parser.source.value
            result.sources[source] = result.sources.get(source, 0) + 1

        result.documents = list(documents.values())
        logger.info(
            "Normalized %s of %s records: %s, unrecognised %s",
            len(result.documents),
            len(resumes),
            result.sources or "nothing",
            result.skipped,
        )
        return result

    def _parser_for(self, raw: dict[str, Any]) -> BaseResumeParser | None:
        """Return the parser the record belongs to, if there is one."""
        # An export also carries manifests and rows of other tables.
        for parser in self.parsers:
            if parser.matches(raw=raw):
                return parser
        return None
