from typing import TYPE_CHECKING, Annotated, Any, ClassVar, final
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from services.api.common.schemas import CamelCaseModel
from services.api.resumes.constants import (
    DEFAULT_PAGE_SIZE,
    EMPTY_REQUIREMENTS,
    LONG_REQUIREMENTS,
    MAX_PAGE_SIZE,
    MAX_REQUIREMENTS,
    MAX_UPLOAD_BYTES,
    PLAN_ACTION,
)
from services.enrichment.schemas import (
    EducationLevel,
    Employment,
    ResumeFilters,
    VacancyBrief,
    WorkFormat,
)
from services.search_engines.schemas import MAX_WEIGHT, SearchWeights

if TYPE_CHECKING:
    from apps.resumes.models import ResumeUpload


@final
class LanguagePayload(CamelCaseModel):
    """A language requirement exchanged over the API."""

    code: str
    min_level: str | None = None


@final
class ResumeFiltersPayload(CamelCaseModel):
    """Search criteria as the API exposes them."""

    semantic_query: str = ""
    role_query: str = ""
    must_keywords: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    optional_keywords: list[str] = Field(default_factory=list)
    professional_roles: list[str] = Field(default_factory=list)
    min_experience_years: int | None = None
    min_tenure_months: int | None = None
    areas: list[str] = Field(default_factory=list)
    work_formats: list[WorkFormat] = Field(default_factory=list)
    employments: list[Employment] = Field(default_factory=list)
    education_levels: list[EducationLevel] = Field(default_factory=list)
    languages: list[LanguagePayload] = Field(default_factory=list)
    max_salary: int | None = None

    @classmethod
    def from_domain(cls, filters: ResumeFilters) -> ResumeFiltersPayload:
        """Build the wire representation of extracted filters."""
        return cls.model_validate(obj=filters.model_dump())


@final
class ResumeSearchRequest(CamelCaseModel):
    """Describe a resume search request."""

    # A misspelled field is a search run on criteria nobody asked for.
    model_config = ConfigDict(extra="forbid")

    vacancy: str = Field(
        min_length=1,
        max_length=MAX_REQUIREMENTS,
        description="The vacancy as the hiring side wrote it.",
    )
    general: str = Field(
        default="",
        max_length=MAX_REQUIREMENTS,
        description=(
            "What every candidate of this company is asked for: education, "
            "languages, city, work format. Never read as the profession."
        ),
    )
    recruiter: str = Field(
        default="",
        max_length=MAX_REQUIREMENTS,
        description=(
            "What the recruiter knows on top of the vacancy text. Where "
            "it contradicts the vacancy, the recruiter wins."
        ),
    )
    filters: ResumeFilters | None = Field(
        default=None,
        description=(
            "Criteria to search by as they are, skipping extraction. This "
            "is what the review page sends back once they were edited."
        ),
    )
    weights: SearchWeights = Field(
        default_factory=SearchWeights,
        description="What each part of the ranking counts for.",
    )
    size: Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE
    offset: Annotated[int, Field(ge=0)] = 0

    def brief(self) -> VacancyBrief:
        """Return the three texts as the enricher reads them."""
        return VacancyBrief(
            vacancy=self.vacancy,
            general=self.general,
            recruiter=self.recruiter,
        )


@final
class ResumeSearchForm(CamelCaseModel):
    """The same search request as the form page submits it."""

    # Anything typed in is a string, and the page reports its own errors.
    vacancy: str = ""
    general: str = ""
    recruiter: str = ""
    size: str = str(DEFAULT_PAGE_SIZE)

    def error(self) -> str:
        """Return what keeps the form from being searched with, if anything."""
        # Checked before the request is built, which is what rejects them.
        if not self.vacancy.strip():
            return EMPTY_REQUIREMENTS
        if self._length() > MAX_REQUIREMENTS:
            return LONG_REQUIREMENTS
        return ""

    def _length(self) -> int:
        """Return how much text the three fields hold together."""
        return len(self.vacancy) + len(self.general) + len(self.recruiter)

    def to_request(self) -> ResumeSearchRequest:
        """Return the request this form stands for."""
        return ResumeSearchRequest(
            vacancy=self.vacancy,
            general=self.general,
            recruiter=self.recruiter,
            size=self._size(),
        )

    def _size(self) -> int:
        """Return how many candidates the page asks for."""
        wanted = int(self.size) if self.size.isdigit() else DEFAULT_PAGE_SIZE
        return min(max(wanted, 1), MAX_PAGE_SIZE)


@final
class PlanItem(BaseModel):
    """One extracted criterion, as the panel offers it."""

    # The token is what comes back when the box stays ticked.
    token: str
    label: str
    checked: bool = True


@final
class PlanGroup(BaseModel):
    """The criteria of one kind, drawn as one row of boxes."""

    key: str
    title: str
    items: list[PlanItem] = Field(default_factory=list)


@final
class PlanSlider(BaseModel):
    """One weight of the ranking, drawn as one slider."""

    key: str
    title: str
    hint: str
    value: float


@final
class PlanPanel(BaseModel):
    """The criteria a search runs on, laid out to be edited."""

    vacancy: str = ""
    general: str = ""
    recruiter: str = ""
    size: int = DEFAULT_PAGE_SIZE
    semantic_query: str = ""
    role_query: str = ""
    groups: list[PlanGroup] = Field(default_factory=list)
    sliders: list[PlanSlider] = Field(default_factory=list)
    action: str = PLAN_ACTION
    filters: str = Field(
        default="",
        description="The criteria as JSON, carried through the page hidden.",
    )
    plan_id: str = Field(
        default="",
        description="The stored search these criteria and weights belong to.",
    )


@final
class ResumePlanForm(CamelCaseModel):
    """The review panel as the browser sends it back."""

    # Every box that stayed ticked posts under this one name.
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset({"keep"})

    vacancy: str = ""
    general: str = ""
    recruiter: str = ""
    size: str = str(DEFAULT_PAGE_SIZE)
    filters: str = ""
    plan_id: str = ""
    semantic_query: str = ""
    role_query: str = ""
    keep: list[str] = Field(default_factory=list)
    lexical: str = ""
    semantic: str = ""
    technology: str = ""
    role: str = ""
    preference: str = ""

    def weights(self) -> SearchWeights:
        """Return the weights the sliders were left at."""
        moved = {
            key: self._number(value=value)
            for key, value in (
                ("lexical", self.lexical),
                ("semantic", self.semantic),
                ("technology", self.technology),
                ("role", self.role),
                ("preference", self.preference),
            )
        }
        return SearchWeights(
            **{
                key: value for key, value in moved.items() if value is not None
            },
        )

    def page_size(self) -> int:
        """Return how many candidates the panel asks for."""
        wanted = int(self.size) if self.size.isdigit() else DEFAULT_PAGE_SIZE
        return min(max(wanted, 1), MAX_PAGE_SIZE)

    @staticmethod
    def _number(value: str) -> float | None:
        """Return one slider as a weight, or nothing if it is not one."""
        try:
            weight = float(value)
        except ValueError:
            return None
        return min(max(weight, 0.0), MAX_WEIGHT)


@final
class ResumeUploadFile(BaseModel):
    """The file an upload is accepted by, before it is opened."""

    name: str
    size: Annotated[int, Field(gt=0, le=MAX_UPLOAD_BYTES)]


@final
class ResumeUploadPayload(BaseModel):
    """The files one upload request carries."""

    file: ResumeUploadFile


@final
class ResumeUploadPath(BaseModel):
    """The upload a status request points at."""

    upload_id: UUID


@final
class ResumeUploadStatus(CamelCaseModel):
    """Where an upload got to and what it changed in the index."""

    id: UUID
    status: str
    indexed: int
    unchanged: int
    skipped: int
    chunks: int
    sources: dict[str, int] = Field(
        default_factory=dict,
        description="How many resumes came from each known source.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="The files that could not be indexed, and why.",
    )

    @classmethod
    def from_upload(cls, upload: ResumeUpload) -> ResumeUploadStatus:
        """Build the wire view of a stored upload."""
        return cls.model_validate(obj=upload)


@final
class MatchedChunk(CamelCaseModel):
    """A fragment of an experience description that matched."""

    text: str
    score: float


@final
class MatchedExperience(CamelCaseModel):
    """The job whose description matched the requirements."""

    position: str | None = None
    company: str | None = None
    start: str | None = None
    end: str | None = None
    score: float
    chunks: list[MatchedChunk] = Field(default_factory=list)


@final
class ResumeHit(CamelCaseModel):
    """A single ranked candidate."""

    id: str
    score: float
    title: str | None = None
    alternate_url: str | None = None
    area: str | None = None
    age: int | None = None
    total_experience_months: int | None = None
    salary_amount: int | None = None
    salary_currency: str | None = None
    skill_set: list[str] = Field(default_factory=list)
    matched_experience: list[MatchedExperience] = Field(
        default_factory=list,
        description=(
            "Why this resume ranked where it did: the jobs and the "
            "description fragments closest to the requirements."
        ),
    )


@final
class ResumeSearchResponse(CamelCaseModel):
    """Return the ranked candidates for a set of requirements."""

    total: int
    filters: ResumeFiltersPayload = Field(
        description="The criteria actually used, after extraction.",
    )
    items: list[ResumeHit] = Field(default_factory=list)


@final
class DashboardEducation(BaseModel):
    """One education entry as the dashboard renders it."""

    year: int | None = None
    name: str = ""
    result: str = ""


@final
class DashboardExperience(BaseModel):
    """One job as the dashboard renders it."""

    period: str = ""
    duration: str = ""
    company: str = ""
    area: str = ""
    industries: list[str] = Field(default_factory=list)
    position: str = ""
    description: str = ""
    matched: bool = False


@final
class DashboardResume(BaseModel):
    """One ranked candidate laid out as a resume page."""

    rank: int
    score: float
    id: str
    url: str = ""
    title: str = ""
    area: str = ""
    age: int | None = None
    gender: str = ""
    salary: str = ""
    total_experience: str = ""
    roles: list[str] = Field(default_factory=list)
    work_formats: list[str] = Field(default_factory=list)
    employments: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    education_level: str = ""
    education: list[DashboardEducation] = Field(default_factory=list)
    experience: list[DashboardExperience] = Field(default_factory=list)
    skill_set: list[str] = Field(default_factory=list)
    about: str = ""


@final
class PoolRow(BaseModel):
    """One candidate of the pool as the browser re-sorts it."""

    id: str
    url: str = ""
    title: str = ""
    area: str = ""
    age: int | None = None
    experience: str = ""
    salary: str = ""
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="What this candidate is worth on each criterion, 0 to 1.",
    )


@final
class DashboardContext(BaseModel):
    """Everything the dashboard template renders."""

    total: int
    filters: ResumeFiltersPayload
    plan: PlanPanel = Field(
        default_factory=PlanPanel,
        description="The same panel again, so the weights can be moved.",
    )
    pool: list[PoolRow] = Field(
        default_factory=list,
        description=(
            "Every candidate the criteria reached, already scored. The "
            "sliders re-sort this in the browser without asking again."
        ),
    )
    resumes: list[DashboardResume] = Field(default_factory=list)

    @property
    def pool_data(self) -> list[dict[str, Any]]:
        """Return the pool the way the page hands it to the script."""
        return [row.model_dump() for row in self.pool]

    @property
    def criteria(self) -> dict[str, str]:
        """Return what each criterion is called, for the list to label it."""
        return {slider.key: slider.title for slider in self.plan.sliders}
