from typing import final

from services.search_engines.open_search import OpenSearchBackend

__all__ = ["SearchEngines"]


@final
class SearchEngines:
    """Give out the search backend a service is to run on, by name."""

    # Every backend gives out the same pair: get_engine() and get_index().
    open_search = OpenSearchBackend
