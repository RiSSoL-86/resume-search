from typing import final, override

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document

from services.indexing.chunking.base import BaseChunker
from services.indexing.chunking.text import segments
from services.indexing.chunking.utils import merge_short
from services.indexing.constants import CHUNK_OVERLAP, CHUNK_SIZE


@final
class StructuralChunker(BaseChunker):
    """Group the bullet lines of a description into sized chunks."""

    def __init__(self) -> None:
        """Configure the fallback splitter for oversized lines."""
        self.splitter = SentenceSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

    @override
    async def split(self, description: str) -> list[str]:
        """Return the chunks of a single description."""
        chunks: list[str] = []
        buffer = ""
        for line in segments(text=description):
            if len(line) > CHUNK_SIZE:
                if buffer:
                    chunks.append(buffer)
                    buffer = ""
                chunks.extend(self._split_long(line=line))
                continue

            candidate = f"{buffer}\n{line}" if buffer else line
            if len(candidate) > CHUNK_SIZE:
                chunks.append(buffer)
                buffer = line
            else:
                buffer = candidate

        if buffer:
            chunks.append(buffer)

        return merge_short(chunks=chunks)

    def _split_long(self, line: str) -> list[str]:
        """Split a single oversized line on sentence boundaries."""
        nodes = self.splitter.get_nodes_from_documents(
            documents=[Document(text=line)],
        )
        return [node.get_content().strip() for node in nodes]
