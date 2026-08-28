from collections.abc import Sequence
from typing import TYPE_CHECKING, final

from services.search_engines.open_search.constants import (
    BRIEF_FIELDS,
    DESCRIPTION_KEYWORDS_BOOST,
    EXPERIENCE_SCORE_MODE,
    HEAD_VECTOR_BOOST,
    INNER_HITS_SIZE,
    KEYWORD_FIELDS,
    KNN_CANDIDATES,
    LANGUAGE_LEVELS,
    MIN_ROLE_MONTHS,
    MONTHS_PER_YEAR,
    MUST_KEYWORDS_BOOST,
    REQUIRED_KEYWORDS_BOOST,
    ROLE_TENURE_FACTOR,
    SHORT_ROLE_WEIGHT,
    SOURCE_EXCLUDES,
    SPELLING_SEPARATOR,
)
from services.search_engines.schemas import Clause, SearchColumn

if TYPE_CHECKING:
    from services.enrichment.schemas import (
        LanguageRequirement,
        ResumeFilters,
    )
    from services.search_engines.schemas import QueryVectors


@final
class Requirements:
    """The criteria a candidate cannot be ranked without."""

    def __init__(self, filters: ResumeFilters) -> None:
        """Take the criteria the vacancy was read into."""
        self.filters = filters

    def clauses(self) -> list[Clause]:
        """Return the clauses every half of the ranking is filtered by."""
        # Years worked is the one requirement every resume states.
        if self.filters.min_experience_years is None:
            return []

        months = self.filters.min_experience_years * MONTHS_PER_YEAR
        return [{"range": {"total_experience.months": {"gte": months}}}]


@final
class Preferences:
    """The criteria that lift a candidate but never drop one."""

    def __init__(self, filters: ResumeFilters) -> None:
        """Take the criteria the vacancy was read into."""
        self.filters = filters

    def clauses(self) -> list[Clause]:
        """Return every clause a candidate is only rewarded for answering."""
        wanted: dict[str, Sequence[str]] = {
            "work_format.id": self.filters.work_formats,
            "employments.id": self.filters.employments,
            "education.level.id": self.filters.education_levels,
        }

        clauses: list[Clause] = []
        if self.filters.areas:
            clauses.append(self.area())
        clauses.extend(
            self.terms(field=field, values=values)
            for field, values in wanted.items()
            if values
        )

        # As gates these two cut the fitting candidates hardest.
        clauses.extend(
            self.language(requirement=requirement)
            for requirement in self.filters.languages
        )
        if self.filters.max_salary is not None:
            clauses.append(self.salary(maximum=self.filters.max_salary))
        if self.filters.min_tenure_months is not None:
            clauses.append(
                self.stability(months=self.filters.min_tenure_months),
            )
        return clauses

    @staticmethod
    def terms(field: str, values: Sequence[str]) -> Clause:
        """Return a clause rewarding any of the wanted values of a field."""
        # Every preference counts the same; the slider weighs them together.
        return {"terms": {field: list(values)}}

    def area(self) -> Clause:
        """Return a clause rewarding living in or moving to the wanted city."""
        return {
            "bool": {
                "should": [
                    {"terms": {"area.name": self.filters.areas}},
                    {"terms": {"relocation.area.name": self.filters.areas}},
                ],
                "minimum_should_match": 1,
            },
        }

    def language(self, requirement: LanguageRequirement) -> Clause:
        """Return a clause rewarding one language at the wanted level."""
        must: list[Clause] = [{"term": {"language.id": requirement.code}}]
        if requirement.min_level:
            enough = LANGUAGE_LEVELS.index(requirement.min_level)
            levels = list(LANGUAGE_LEVELS[enough:])
            must.append({"terms": {"language.level.id": levels}})

        return {
            "nested": {"path": "language", "query": {"bool": {"must": must}}},
        }

    @staticmethod
    def stability(months: int) -> Clause:
        """Return a clause rewarding a candidate who stays in one place."""
        # Half the jobs at least this long. A job just started is not
        # counted at all, so a recent move costs a good candidate nothing.
        return {"range": {"tenure.median_months": {"gte": months}}}

    @staticmethod
    def salary(maximum: int) -> Clause:
        """Return a clause rewarding an expectation within the budget."""
        # A resume without a stated expectation is not a mismatch.
        return {
            "bool": {
                "should": [
                    {"range": {"salary.amount": {"lte": maximum}}},
                    {
                        "bool": {
                            "must_not": {"exists": {"field": "salary.amount"}},
                        },
                    },
                ],
                "minimum_should_match": 1,
            },
        }


@final
class Technologies:
    """The wanted technologies, scored over the jobs that describe them."""

    def __init__(self, filters: ResumeFilters) -> None:
        """Take the criteria the vacancy was read into."""
        self.filters = filters

    def scored(self) -> set[str]:
        """Return every spelling this half already scores on its own."""
        named = self.filters.must_keywords + self.filters.required_keywords
        return {
            spelling
            for keyword in named
            for spelling in keyword.split(SPELLING_SEPARATOR)
        }

    def query(self) -> Clause | None:
        """Return the half scoring the technologies, if any were named."""
        # Boosted inside the lexical half these are flattened away.
        should = [
            *self.clauses(
                keywords=self.filters.must_keywords,
                boost=MUST_KEYWORDS_BOOST,
            ),
            *self.clauses(
                keywords=self.filters.required_keywords,
                boost=REQUIRED_KEYWORDS_BOOST,
            ),
        ]
        if not should:
            return None
        return {"bool": {"should": should, "minimum_should_match": 1}}

    def clauses(self, keywords: list[str], boost: float) -> list[Clause]:
        """Return a clause per technology, counted across the whole career."""
        return [
            {
                "nested": {
                    "path": "experience",
                    "score_mode": "sum",
                    "query": self.described(keyword=keyword),
                    "boost": boost,
                },
            }
            for keyword in keywords
        ]

    @staticmethod
    def described(keyword: str) -> Clause:
        """Return a filter on jobs whose description names the technology."""
        # Counting jobs, not relevance: BM25 would punish fuller wording.
        return {
            "constant_score": {
                "filter": {
                    "bool": {
                        "should": [
                            {
                                "match_phrase": {
                                    "experience.description": spelling,
                                },
                            }
                            for spelling in keyword.split(SPELLING_SEPARATOR)
                        ],
                        "minimum_should_match": 1,
                    },
                },
            },
        }


@final
class LexicalQuery:
    """The criterion ranking a resume by the words it is written in."""

    def __init__(self, filters: ResumeFilters) -> None:
        """Take the criteria the vacancy was read into."""
        self.filters = filters

    def query(self) -> Clause:
        """Return the BM25 criterion of the ranking."""
        should: list[Clause] = [self.text(), *self.keywords()]
        return {"bool": {"should": should, "minimum_should_match": 1}}

    def text(self) -> Clause:
        """Return the clause matching the vacancy against the whole resume."""
        # Skills reach this through full_text, whichever field a source fills.
        return {
            "multi_match": {
                "query": self.filters.semantic_query,
                "fields": ["full_text", "title^2"],
                "type": "best_fields",
            },
        }

    def keywords(self) -> list[Clause]:
        """Return the clauses scoring the terms only this half scores."""
        # A higher tier is scored in the technology half already.
        scored = Technologies(filters=self.filters).scored()

        clauses: list[Clause] = []
        for keyword in self.filters.optional_keywords:
            if keyword in scored:
                continue
            clauses.append(
                {
                    "multi_match": {
                        "query": keyword,
                        "fields": KEYWORD_FIELDS,
                        "type": "phrase",
                    },
                },
            )
            clauses.append(
                {
                    "nested": {
                        "path": "experience",
                        "score_mode": EXPERIENCE_SCORE_MODE,
                        "query": {
                            "match_phrase": {
                                "experience.description": keyword,
                            },
                        },
                        "boost": DESCRIPTION_KEYWORDS_BOOST,
                    },
                },
            )
        return clauses


@final
class RoleQuery:
    """The criterion ranking a resume by the role it was earned in."""

    def __init__(self, filters: ResumeFilters) -> None:
        """Take the criteria the vacancy was read into."""
        self.filters = filters

    def query(self) -> Clause | None:
        """Return the criterion scoring the wanted role, if one was named."""
        if not self.filters.professional_roles:
            return None
        return {
            "bool": {"should": self.clauses(), "minimum_should_match": 1},
        }

    def clauses(self) -> list[Clause]:
        """Return the clauses scoring the role a candidate has held."""
        roles = " ".join(self.filters.professional_roles)
        return [
            {
                "multi_match": {
                    "query": roles,
                    "fields": ["title^3", "professional_roles.name^2"],
                    "type": "best_fields",
                },
            },
            {
                "nested": {
                    "path": "experience",
                    "score_mode": EXPERIENCE_SCORE_MODE,
                    "query": {
                        "match": {"experience.position": {"query": roles}},
                    },
                },
            },
            self.tenure(),
        ]

    def tenure(self) -> Clause:
        """Return the clause scoring the years spent in the wanted role."""
        # Every word of the role must be there, and a short stint is cheap.
        positions = {
            "bool": {
                "should": [
                    {
                        "match": {
                            "experience.position": {
                                "query": role,
                                "operator": "and",
                            },
                        },
                    }
                    for role in self.filters.professional_roles
                ],
                "minimum_should_match": 1,
            },
        }
        return {
            "nested": {
                "path": "experience",
                "score_mode": "sum",
                "query": {
                    "function_score": {
                        "query": positions,
                        "functions": [
                            {
                                "filter": self.lasted("gte", MIN_ROLE_MONTHS),
                                "field_value_factor": {
                                    "field": "experience.duration_months",
                                    "factor": ROLE_TENURE_FACTOR,
                                    "modifier": "ln1p",
                                    "missing": 0,
                                },
                            },
                            {
                                "filter": self.lasted("lt", MIN_ROLE_MONTHS),
                                "weight": SHORT_ROLE_WEIGHT,
                            },
                        ],
                        "score_mode": "sum",
                        "boost_mode": "replace",
                    },
                },
            },
        }

    @staticmethod
    def lasted(bound: str, months: int) -> Clause:
        """Return a clause selecting jobs by how long they lasted."""
        return {"range": {"experience.duration_months": {bound: months}}}


@final
class SemanticQuery:
    """The half ranking a resume by what its jobs were about."""

    def __init__(self, filters: ResumeFilters, vectors: QueryVectors) -> None:
        """Take the criteria the vacancy was read into and their vectors."""
        self.filters = filters
        self.vectors = vectors

    def query(self, inner_hits: bool) -> Clause:
        """Return the vector half of the ranking."""
        # The best chunk scores the job, the best job scores the resume.
        chunks = self.chunks()
        should: list[Clause] = [{"nested": chunks}]
        if self.vectors.head:
            should.append(self.head())

        jobs: Clause = {
            "path": "experience",
            "score_mode": EXPERIENCE_SCORE_MODE,
            "query": {"bool": {"should": should, "minimum_should_match": 1}},
        }
        if inner_hits:
            chunks["inner_hits"] = {
                "name": "chunk",
                "size": INNER_HITS_SIZE,
                "_source": ["experience.description_chunks.text"],
            }
            jobs["inner_hits"] = {
                "name": "experience",
                "size": INNER_HITS_SIZE,
                "_source": [
                    "experience.position",
                    "experience.company",
                    "experience.start",
                    "experience.end",
                ],
            }
        return {"bool": {"must": [{"nested": jobs}]}}

    def chunks(self) -> Clause:
        """Return the clause matching the vacancy against job descriptions."""
        return {
            "path": "experience.description_chunks",
            "score_mode": "max",
            "query": {
                "knn": {
                    "experience.description_chunks.vector": {
                        "vector": self.vectors.description,
                        "k": KNN_CANDIDATES,
                    },
                },
            },
        }

    def head(self) -> Clause:
        """Return the clause matching the wanted role against job titles."""
        return {
            "knn": {
                "experience.head_vector": {
                    "vector": self.vectors.head,
                    "k": KNN_CANDIDATES,
                    "boost": HEAD_VECTOR_BOOST,
                },
            },
        }


@final
class ResumeQueryBuilder:
    """Build the request bodies the engine sends."""

    @staticmethod
    def build_columns(
        filters: ResumeFilters,
        vectors: QueryVectors,
    ) -> list[SearchColumn]:
        """Return one query per criterion the ranking is made of."""
        # Every criterion is scored on its own, whatever its weight is now:
        # that is what lets a moved slider re-rank without asking again.
        preferences = Preferences(filters=filters).clauses()
        built: list[tuple[str, Clause | None, bool]] = [
            ("lexical", LexicalQuery(filters=filters).query(), False),
            (
                "semantic",
                SemanticQuery(filters=filters, vectors=vectors).query(
                    inner_hits=False,
                ),
                False,
            ),
            ("technology", Technologies(filters=filters).query(), True),
            ("role", RoleQuery(filters=filters).query(), False),
            (
                "preference",
                {"bool": {"should": preferences, "minimum_should_match": 1}}
                if preferences
                else None,
                False,
            ),
        ]
        return [
            SearchColumn(key=key, query=query, from_zero=from_zero)
            for key, query, from_zero in built
            if query is not None
        ]

    def build_column_body(
        self,
        filters: ResumeFilters,
        query: Clause,
        size: int,
    ) -> Clause:
        """Return the request scoring one criterion of the ranking."""
        # Ranking needs ids and scores; the second pass fetches bodies.
        return {
            "size": size,
            "_source": False,
            "track_total_hits": True,
            "query": {
                "bool": {
                    "must": [query],
                    "filter": Requirements(filters=filters).clauses(),
                },
            },
        }

    @staticmethod
    def build_brief_body(resume_ids: list[str]) -> Clause:
        """Return a request fetching the little the pool list shows."""
        # The whole pool travels to the browser, so it travels light.
        return {
            "size": len(resume_ids),
            "_source": {"includes": BRIEF_FIELDS},
            "query": {"bool": {"filter": [{"ids": {"values": resume_ids}}]}},
        }

    def build_matches_body(
        self,
        filters: ResumeFilters,
        vectors: QueryVectors,
        resume_ids: list[str],
    ) -> Clause:
        """Return a request that fetches and explains the given resumes."""
        # `should`, so explaining a resume never narrows the page.
        explained = SemanticQuery(filters=filters, vectors=vectors).query(
            inner_hits=True,
        )
        return {
            "size": len(resume_ids),
            "_source": {"excludes": SOURCE_EXCLUDES},
            "query": {
                "bool": {
                    "filter": [{"ids": {"values": resume_ids}}],
                    "should": [explained],
                },
            },
        }
