from typing import final

from services.enrichment.open_ai import OpenAIBackend

__all__ = ["Enrichers"]


@final
class Enrichers:
    """Give out the enrichment provider a service is to run on, by name."""

    # Every provider gives out the same thing: get_enricher().
    open_ai = OpenAIBackend
