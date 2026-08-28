from typing import TYPE_CHECKING, Any, final, override

from apps.common.services.base import BaseService
from services.api.resumes.schemas import (
    DashboardContext,
    DashboardEducation,
    DashboardExperience,
    DashboardResume,
    PoolRow,
    ResumeFiltersPayload,
    ResumeSearchRequest,
)
from services.api.resumes.services.plan import ResumePlanService
from services.api.resumes.services.search import ResumeSearchService
from services.api.resumes.utils import (
    format_duration,
    format_period,
    format_salary,
)

if TYPE_CHECKING:
    from services.search_engines.schemas import PoolCandidate, ResumeDocument


@final
class ResumeDashboardService(BaseService):
    """Lay the ranked resumes out the way a resume page reads."""

    def __init__(self) -> None:
        """Rank through the same service the JSON endpoint runs on."""
        self.search = ResumeSearchService()
        self.plans = ResumePlanService()

    @override
    async def execute(
        self,
        payload: ResumeSearchRequest,
    ) -> DashboardContext:
        """Return the ranked candidates ready to be rendered."""
        filters, result = await self.search.rank(payload=payload)
        plan = await self.plans.remember(
            payload=payload,
            filters=filters,
            matrix=result.matrix,
            total=result.total,
        )

        return DashboardContext(
            total=result.total,
            filters=ResumeFiltersPayload.from_domain(filters=filters),
            plan=ResumePlanService.build(
                payload=payload,
                filters=filters,
                plan_id=str(plan.id),
            ),
            pool=[
                self._build_row(candidate=candidate)
                for candidate in result.matrix.candidates
            ],
            resumes=[
                self._build_resume(
                    resume=resume,
                    rank=payload.offset + position,
                )
                for position, resume in enumerate(result.resumes, start=1)
            ],
        )

    @classmethod
    def _build_resume(
        cls,
        resume: ResumeDocument,
        rank: int,
    ) -> DashboardResume:
        """Build one candidate card out of the indexed resume."""
        source = resume.source
        salary = source.get("salary") or {}
        education = source.get("education") or {}
        # A job counts as matched when the engine explained the hit with it.
        matched = {(match.position, match.company) for match in resume.matches}

        return DashboardResume(
            rank=rank,
            score=resume.score,
            id=resume.id,
            url=source.get("alternate_url") or "",
            title=source.get("title") or "",
            area=cls._name(value=source.get("area")),
            age=source.get("age"),
            gender=cls._name(value=source.get("gender")),
            salary=format_salary(
                amount=salary.get("amount"),
                currency=salary.get("currency"),
            ),
            total_experience=format_duration(
                months=(source.get("total_experience") or {}).get("months"),
            ),
            roles=cls._names(values=source.get("professional_roles")),
            work_formats=cls._names(values=source.get("work_format")),
            employments=cls._names(values=source.get("employment_form")),
            languages=cls._languages(values=source.get("language")),
            education_level=cls._name(value=education.get("level")),
            education=cls._education(values=education.get("primary")),
            experience=cls._experience(
                values=source.get("experience"),
                matched=matched,
            ),
            skill_set=source.get("skill_set") or [],
            about=source.get("skills") or "",
        )

    @classmethod
    def _build_row(cls, candidate: PoolCandidate) -> PoolRow:
        """Build one line of the list the sliders re-sort."""
        source = candidate.source
        salary = source.get("salary") or {}

        return PoolRow(
            id=candidate.id,
            url=source.get("alternate_url") or "",
            title=source.get("title") or "",
            area=cls._name(value=source.get("area")),
            age=source.get("age"),
            experience=format_duration(
                months=(source.get("total_experience") or {}).get("months"),
            ),
            salary=format_salary(
                amount=salary.get("amount"),
                currency=salary.get("currency"),
            ),
            scores=candidate.scores,
        )

    @classmethod
    def _experience(
        cls,
        values: Any,
        matched: set[tuple[str | None, str | None]],
    ) -> list[DashboardExperience]:
        """Build the career history, newest job first."""
        return [
            DashboardExperience(
                period=format_period(
                    start=entry.get("start"),
                    end=entry.get("end"),
                ),
                duration=format_duration(months=entry.get("duration_months")),
                company=entry.get("company") or "",
                area=cls._name(value=entry.get("area")),
                industries=cls._names(values=entry.get("industries")),
                position=entry.get("position") or "",
                description=entry.get("description") or "",
                matched=(entry.get("position"), entry.get("company"))
                in matched,
            )
            for entry in (values or [])
            if isinstance(entry, dict)
        ]

    @classmethod
    def _education(cls, values: Any) -> list[DashboardEducation]:
        """Build the education entries."""
        return [
            DashboardEducation(
                year=entry.get("year"),
                name=entry.get("name") or "",
                result=entry.get("result") or "",
            )
            for entry in (values or [])
            if isinstance(entry, dict)
        ]

    @classmethod
    def _languages(cls, values: Any) -> list[str]:
        """Build the "Русский — Родной" lines."""
        languages = []
        for entry in values or []:
            if not isinstance(entry, dict):
                continue
            level = cls._name(value=entry.get("level"))
            name = entry.get("name") or ""
            languages.append(f"{name} — {level}" if level else name)
        return languages

    @staticmethod
    def _name(value: Any) -> str:
        """Return the readable name of a reference object."""
        if not isinstance(value, dict):
            return ""
        return value.get("name") or ""

    @classmethod
    def _names(cls, values: Any) -> list[str]:
        """Return the readable names of a list of reference objects."""
        names = [cls._name(value=entry) for entry in values or []]
        return [name for name in names if name]
