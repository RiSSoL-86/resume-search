from copy import deepcopy
from datetime import date
from statistics import mean, median
from typing import Any, final

from services.indexing.constants import MONTHS_IN_YEAR
from services.indexing.directories.companies import CompanyDirectory


@final
class ResumeExperience:
    """The jobs of one resume and everything derived from them."""

    def __init__(self, raw: dict[str, Any], today: date) -> None:
        """Take the resume and the day its ongoing jobs are measured to."""
        self.raw = raw
        self.today = today

    def heads(self) -> list[tuple[int, str]]:
        """Return the "position — company" line of each job, with its index."""
        # Embedded apart: a job title is the strongest signal a resume has.
        heads = []
        for position, entry in self._entries(experience=self.raw):
            parts = (entry.get("position") or "", entry.get("company") or "")
            head = " — ".join(part.strip() for part in parts if part.strip())
            if head:
                heads.append((position, head))
        return heads

    def descriptions(self) -> list[tuple[int, str]]:
        """Return the non-empty job descriptions with their index."""
        descriptions = []
        for position, entry in self._entries(experience=self.raw):
            description = (entry.get("description") or "").strip()
            if description:
                descriptions.append((position, description))
        return descriptions

    def document(self) -> dict[str, Any]:
        """Return the resume with everything computed from its own jobs."""
        # Kept out of the fingerprint: an ongoing job grows every month.
        document = deepcopy(self.raw)
        for _, entry in self._entries(experience=document):
            entry["duration_months"] = self.duration_months(entry=entry)
            entry["company_key"] = self._company_key(entry=entry)

        document["tenure"] = self.tenure()
        document["last_job"] = self.last_job()
        document["company_ids"] = self.company_ids()
        document["company_keys"] = self.company_keys()
        document["industry_ids"] = self.industry_ids()
        return document

    def tenure(self) -> dict[str, Any]:
        """Return how long this person tends to hold one job."""
        history = self.history()
        if not history:
            return {}

        durations = [months for months, _ in history]
        counted = self._counted(history=history)
        return {
            "job_count": len(history),
            "average_months": round(mean(counted)),
            "median_months": round(median(counted)),
            "weighted_months": self._weighted(durations=durations),
            "min_months": min(counted),
            "longest_months": max(durations),
            "last_months": durations[0],
            "jobs_under_year": sum(
                1 for months in counted if months < MONTHS_IN_YEAR
            ),
        }

    def last_job(self) -> dict[str, Any]:
        """Return the job the resume ends on, the one a search reads first."""
        history = self.history()
        if not history:
            return {}

        months, entry = history[0]
        return {
            "position": entry.get("position") or "",
            "company": entry.get("company") or "",
            "start": entry.get("start"),
            "end": entry.get("end"),
            "duration_months": months,
            "is_current": not entry.get("end"),
            "industry_ids": self._industries(entry=entry),
        }

    def company_ids(self) -> list[str]:
        """Return every company the resume names, newest first."""
        found = []
        for _, entry in self.history():
            company_id = entry.get("company_id") or (
                entry.get("employer") or {}
            ).get("id")
            if company_id and str(company_id) not in found:
                found.append(str(company_id))
        return found

    def company_keys(self) -> list[str]:
        """Return every employer by name, for the ones no id is known for."""
        found = []
        for _, entry in self.history():
            key = self._company_key(entry=entry)
            if key and key not in found:
                found.append(key)
        return found

    def industry_ids(self) -> list[str]:
        """Return every industry the resume worked in, newest first."""
        found = []
        for _, entry in self.history():
            for industry_id in self._industries(entry=entry):
                if industry_id not in found:
                    found.append(industry_id)
        return found

    def history(self) -> list[tuple[int, dict[str, Any]]]:
        """Return the datable jobs with their length, newest first."""
        history = []
        for _, entry in self._entries(experience=self.raw):
            months = self.duration_months(entry=entry)
            if months is not None:
                history.append((months, entry))
        return sorted(
            history,
            key=lambda job: job[1].get("start") or "",
            reverse=True,
        )

    def duration_months(self, entry: dict[str, Any]) -> int | None:
        """Return how long a single job lasted, in months."""
        start_value = entry.get("start")
        if not start_value:
            return None
        try:
            start = date.fromisoformat(start_value)
            end_value = entry.get("end")
            end = date.fromisoformat(end_value) if end_value else self.today
        except ValueError:
            return None
        return self._months_between(start=start, end=end)

    @staticmethod
    def _counted(history: list[tuple[int, dict[str, Any]]]) -> list[int]:
        """Return the jobs the average is honestly measured over."""
        # A job started this spring says nothing yet about how long one stays.
        counted = [
            months
            for months, entry in history
            if entry.get("end") or months >= MONTHS_IN_YEAR
        ]
        return counted or [months for months, _ in history]

    @staticmethod
    def _weighted(durations: list[int]) -> int:
        """Return the average tilted towards what the person does now."""
        # Seven months a decade ago weighs less than seven months last year.
        weights = [1 / (rank + 1) for rank in range(len(durations))]
        total = sum(
            months * weight
            for months, weight in zip(durations, weights, strict=True)
        )
        return round(total / sum(weights))

    @staticmethod
    def _company_key(entry: dict[str, Any]) -> str:
        """Return the employer name stripped down to what is searchable."""
        return CompanyDirectory.normalize(name=entry.get("company"))

    @staticmethod
    def _industries(entry: dict[str, Any]) -> list[str]:
        """Return the industry ids one job is filed under, both levels."""
        # hh.ru files a job under "43.647", the directory knows it as "43".
        industries = entry.get("industries")
        if isinstance(industries, dict):
            industries = [industries]

        found: list[str] = []
        for industry in industries or []:
            if not isinstance(industry, dict) or not industry.get("id"):
                continue
            industry_id = str(industry["id"])
            for level in (industry_id, industry_id.split(".")[0]):
                if level not in found:
                    found.append(level)
        return found

    @staticmethod
    def _entries(
        experience: dict[str, Any],
    ) -> list[tuple[int, dict[str, Any]]]:
        """Return the jobs that are objects at all, with their position."""
        return [
            (position, entry)
            for position, entry in enumerate(
                experience.get("experience") or []
            )
            if isinstance(entry, dict)
        ]

    @staticmethod
    def _months_between(start: date, end: date) -> int:
        """Return the whole months separating two dates."""
        months = (end.year - start.year) * 12 + (end.month - start.month)
        if end.day < start.day:
            months -= 1
        return max(months, 0)
