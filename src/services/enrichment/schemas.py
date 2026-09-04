from typing import Literal, Self, final

from pydantic import BaseModel, Field, model_validator

WorkFormat = Literal["REMOTE", "ON_SITE", "HYBRID", "FIELD_WORK"]
Employment = Literal["full", "part", "project", "probation", "volunteer"]
EducationLevel = Literal[
    "secondary",
    "special_secondary",
    "unfinished_higher",
    "higher",
    "bachelor",
    "master",
    "candidate",
    "doctor",
]


# What each text is called when the model is shown all three at once.
BRIEF_SECTIONS = (
    ("vacancy", "ТРЕБОВАНИЯ ВАКАНСИИ"),
    ("general", "ОБЩИЕ ТРЕБОВАНИЯ"),
    ("recruiter", "ОТ РЕКРУТЁРА"),
)


@final
class VacancyBrief(BaseModel):
    """The three texts one search is asked for, deliberately kept apart."""

    vacancy: str = Field(
        default="",
        description="The vacancy as the hiring side wrote it.",
    )
    general: str = Field(
        default="",
        description="What every candidate of this company is asked for.",
    )
    recruiter: str = Field(
        default="",
        description="What the recruiter knows on top of the vacancy text.",
    )

    def as_text(self) -> str:
        """Return the three texts as one, each under its own heading."""
        # Told apart, so the model can weigh them differently.
        written = [
            (heading, getattr(self, section).strip())
            for section, heading in BRIEF_SECTIONS
        ]
        return "\n\n".join(
            f"{heading}:\n{text}" for heading, text in written if text
        )

    def length(self) -> int:
        """Return how much text the model is asked to read."""
        return sum(
            len(getattr(self, section)) for section, _ in BRIEF_SECTIONS
        )


@final
class LanguageRequirement(BaseModel):
    """A language a candidate is expected to know."""

    code: str = Field(
        description="ISO-639-3 code as used by hh.ru: rus, eng, deu, fra.",
    )
    min_level: Literal["a1", "a2", "b1", "b2", "c1", "c2", "l1"] | None = (
        Field(
            default=None,
            description="Minimum CEFR level, or l1 for a native speaker.",
        )
    )


@final
class ResumeFilters(BaseModel):
    """Structured search criteria distilled from a vacancy description."""

    semantic_query: str = Field(
        description=(
            "A dense paraphrase of what the person will actually be "
            "doing day to day, written the way a candidate would "
            "describe it in their own experience section. This is "
            "matched against experience descriptions by vector search, "
            "so it must describe work, not formal requirements."
        ),
    )
    role_query: str = Field(
        default="",
        description=(
            "The job title and the business domain in one short line. "
            "This is matched against the job titles a candidate held, so "
            "it must name the position and the industry, nothing else."
        ),
    )
    must_keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Only what the recruiter names in their own section, and only "
            "if they name it as a technology. Weighed above everything "
            "the vacancy text alone implies. Spellings of one technology "
            'go into a single entry, separated by a pipe: "ML|AI|ИИ".'
        ),
    )
    required_keywords: list[str] = Field(
        default_factory=list,
        description=(
            "The two or three terms the vacancy exists for: nobody "
            "without them fits, and not everyone in the profession has "
            "them. Each one a single word or a fixed phrase, spelled the "
            "way a candidate writes it. They rank a resume above the "
            "rest; they never reject one."
        ),
    )
    optional_keywords: list[str] = Field(
        default_factory=list,
        description=(
            "Every other literal term the vacancy names: technologies, "
            "protocols, frameworks, methodologies, document types. They "
            "tell apart the candidates the required terms put level."
        ),
    )
    professional_roles: list[str] = Field(
        default_factory=list,
        description="Job titles, as a candidate would name their position.",
    )
    min_experience_years: int | None = Field(
        default=None,
        description="Minimum total professional experience, in years.",
    )
    min_tenure_months: int | None = Field(
        default=None,
        description=(
            "How long the candidate is expected to hold one job, in "
            "months. Set it when the text asks for someone who does not "
            "hop: 'больше года на одном месте' is 12."
        ),
    )
    areas: list[str] = Field(
        default_factory=list,
        description="Required cities or regions, as written in Russian.",
    )
    work_formats: list[WorkFormat] = Field(default_factory=list)
    employments: list[Employment] = Field(default_factory=list)
    education_levels: list[EducationLevel] = Field(default_factory=list)
    languages: list[LanguageRequirement] = Field(default_factory=list)
    max_salary: int | None = Field(
        default=None,
        description=(
            "Upper bound of the candidate's salary expectation, in RUB "
            "per month. Convert daily rates using 21 working days."
        ),
    )

    @model_validator(mode="after")
    def _drop_recruiter_terms_from_required(self) -> Self:
        """Keep one term from being scored twice at two different weights."""
        # What the recruiter named already outranks everything else.
        named = {keyword.casefold() for keyword in self.must_keywords}
        self.required_keywords = [
            keyword
            for keyword in self.required_keywords
            if keyword.casefold() not in named
        ]
        return self

    @model_validator(mode="after")
    def _drop_role_from_keywords(self) -> Self:
        """Keep the wanted role out of the terms scored as technologies."""
        # The role clauses match a title already; twice ranks all alike.
        roles = [role.casefold() for role in self.professional_roles]
        self.required_keywords = [
            keyword
            for keyword in self.required_keywords
            if not any(
                keyword.casefold() in role or role in keyword.casefold()
                for role in roles
            )
        ]
        return self
