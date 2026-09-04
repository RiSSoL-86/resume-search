from typing import TYPE_CHECKING, Any, final, override
from uuid import UUID

from apps.common.services.base import BaseService
from apps.resumes.models import SearchPlan
from apps.resumes.repository import SearchPlanRepository
from services.api.resumes.constants import (
    LANGUAGE_NAMES,
    PLAN_GROUPS,
    PLAN_LIMITS,
    PLAN_NAMES,
    PLAN_SLIDERS,
)
from services.api.resumes.schemas import (
    PlanGroup,
    PlanItem,
    PlanPanel,
    PlanSlider,
    ResumePlanForm,
    ResumeSearchRequest,
)
from services.api.resumes.services.search import ResumeSearchService
from services.enrichment.schemas import LanguageRequirement, ResumeFilters

if TYPE_CHECKING:
    from services.search_engines.schemas import ScoreMatrix, SearchWeights


@final
class ResumePlanService(BaseService):
    """Show the criteria a search would run on before it runs."""

    def __init__(self) -> None:
        """Extract through the same service the search itself runs on."""
        self.search = ResumeSearchService()
        self.plans = SearchPlanRepository()

    @override
    async def execute(self, payload: ResumeSearchRequest) -> PlanPanel:
        """Return the panel for the criteria the texts were read into."""
        filters = await self.search.resolve_filters(payload=payload)
        return self.build(payload=payload, filters=filters)

    async def remember(
        self,
        payload: ResumeSearchRequest,
        filters: ResumeFilters,
        matrix: ScoreMatrix,
        total: int,
    ) -> SearchPlan:
        """Store the search so its ranking can be re-weighted later."""
        # The matrix is the point: re-weighting it is what a slider does.
        return await self.plans.create(
            instance=SearchPlan(
                vacancy=payload.vacancy,
                general=payload.general,
                recruiter=payload.recruiter,
                filters=filters.model_dump(mode="json"),
                matrix=matrix.model_dump(mode="json"),
                weights=payload.weights.model_dump(),
                total=total,
            ),
        )

    @classmethod
    def build(
        cls,
        payload: ResumeSearchRequest,
        filters: ResumeFilters,
        plan_id: str = "",
    ) -> PlanPanel:
        """Return the panel standing for one set of criteria."""
        return PlanPanel(
            vacancy=payload.vacancy,
            general=payload.general,
            recruiter=payload.recruiter,
            size=payload.size,
            semantic_query=filters.semantic_query,
            role_query=filters.role_query,
            groups=cls._groups(filters=filters),
            sliders=cls._sliders(weights=payload.weights),
            filters=filters.model_dump_json(),
            plan_id=plan_id,
        )

    async def reviewed(self, form: ResumePlanForm) -> ResumeSearchRequest:
        """Return the search the panel asks for, and file its weights."""
        payload = self.request(form=form)

        # Where the sliders were left is the signal the extraction lacks.
        plan = await self._stored(plan_id=form.plan_id)
        if plan is not None:
            await self.plans.remember_weights(
                plan=plan,
                weights=payload.weights.model_dump(),
            )
        return payload

    async def _stored(self, plan_id: str) -> SearchPlan | None:
        """Return the search this panel came from, if it is still known."""
        try:
            primary_key = UUID(plan_id)
        except ValueError:
            return None
        return await self.plans.get(primary_key=primary_key)

    @classmethod
    def request(cls, form: ResumePlanForm) -> ResumeSearchRequest:
        """Return the search the edited panel asks for."""
        # The texts are carried along only to be shown again.
        return ResumeSearchRequest(
            vacancy=form.vacancy,
            general=form.general,
            recruiter=form.recruiter,
            filters=cls._edited(form=form),
            weights=form.weights(),
            size=form.page_size(),
        )

    @classmethod
    def _edited(cls, form: ResumePlanForm) -> ResumeFilters:
        """Return the criteria left after the unticked ones are dropped."""
        filters = ResumeFilters.model_validate_json(json_data=form.filters)
        filters.semantic_query = form.semantic_query
        filters.role_query = form.role_query

        kept = set(form.keep)
        for key, field, _ in PLAN_GROUPS:
            values = getattr(filters, field)
            setattr(
                filters,
                field,
                [
                    value
                    for position, value in enumerate(values)
                    if f"{key}:{position}" in kept
                ],
            )
        for key, field, _ in PLAN_LIMITS:
            if key not in kept:
                setattr(filters, field, None)
        return filters

    @classmethod
    def _groups(cls, filters: ResumeFilters) -> list[PlanGroup]:
        """Return every criterion drawn as a box that can be unticked."""
        groups = [
            PlanGroup(
                key=key,
                title=title,
                items=[
                    PlanItem(
                        token=f"{key}:{position}",
                        label=cls._label(key=key, value=value),
                    )
                    for position, value in enumerate(getattr(filters, field))
                ],
            )
            for key, field, title in PLAN_GROUPS
        ]
        groups.append(cls._limits(filters=filters))
        return [group for group in groups if group.items]

    @staticmethod
    def _limits(filters: ResumeFilters) -> PlanGroup:
        """Return the criteria that are one number rather than a list."""
        return PlanGroup(
            key="limits",
            title="Пороги",
            items=[
                PlanItem(token=key, label=template.format(value))
                for key, field, template in PLAN_LIMITS
                if (value := getattr(filters, field)) is not None
            ],
        )

    @staticmethod
    def _sliders(weights: SearchWeights) -> list[PlanSlider]:
        """Return the weights of the ranking, ready to be moved."""
        return [
            PlanSlider(
                key=key,
                title=title,
                hint=hint,
                value=getattr(weights, key),
            )
            for key, title, hint in PLAN_SLIDERS
        ]

    @staticmethod
    def _label(key: str, value: Any) -> str:
        """Return what one criterion is called in the panel."""
        if isinstance(value, LanguageRequirement):
            name = LANGUAGE_NAMES.get(value.code, value.code)
            level = (value.min_level or "").upper()
            return f"{name} {level}".strip()
        return PLAN_NAMES.get(key, {}).get(str(value), str(value))
