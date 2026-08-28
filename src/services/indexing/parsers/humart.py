from datetime import date, datetime
from typing import TYPE_CHECKING, Any, ClassVar, final, override

from apps.resumes.choices import ResumeSource
from services.indexing.constants import DEFAULT_CURRENCY
from services.indexing.parsers.base import BaseResumeParser
from services.indexing.parsers.text import to_plain_text

if TYPE_CHECKING:
    from services.indexing.directories.companies import CompanyDirectory

# The humart export keeps a name in one line, the index keeps it in three.
_NAME_PARTS = ("last_name", "first_name", "middle_name")


@final
class HumartResumeParser(BaseResumeParser):
    """Read the resumes the humart database exports as one JSON file."""

    source: ClassVar[ResumeSource] = ResumeSource.HUMART

    def __init__(self, directory: CompanyDirectory) -> None:
        """Take the directory the bare company names are looked up in."""
        # Humart names an employer, hh.ru also files it by industry.
        self.directory = directory

    @override
    def matches(self, raw: dict[str, Any]) -> bool:
        """Report whether the record is a humart resume."""
        return bool(raw.get("resume_id")) and isinstance(
            raw.get("work_experience"),
            list,
        )

    @override
    def parse(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Return the record in the shape every indexed resume has."""
        experience = [
            self._job(entry=entry)
            for entry in raw["work_experience"]
            if isinstance(entry, dict)
        ]
        return {
            "id": str(raw["resume_id"]),
            "source": self.source.value,
            "title": raw.get("desired_position") or "",
            **self._name(full_name=raw.get("full_name")),
            "age": (raw.get("age") or {}).get("value"),
            "salary": self._salary(amount=raw.get("salary")),
            "alternate_url": raw.get("source_link"),
            "created_at": self._moment(value=raw.get("resume_created_at")),
            "updated_at": self._moment(value=raw.get("resume_updated_at")),
            # The "about me" text is where humart keeps the competencies.
            "skills": to_plain_text(value=raw.get("about_me")),
            "experience": experience,
            "total_experience": {
                "months": self._months(experience=experience)
            },
            "education": self._education(raw=raw),
            "language": [
                self._language(entry=entry)
                for entry in raw.get("languages") or []
                if isinstance(entry, dict)
            ],
        }

    def _job(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Return one job in the shape the experience mapping expects."""
        # A job still held has no end date, the way hh.ru writes it too.
        end = None if entry.get("toCurrentMoment") else entry.get("to")
        company = entry.get("company") or ""
        return {
            "position": entry.get("position") or "",
            "company": company,
            "start": self._day(value=entry.get("from")),
            "end": self._day(value=end),
            "description": to_plain_text(value=entry.get("responsibilities")),
            **self.directory.lookup(name=company),
        }

    @staticmethod
    def _day(value: Any) -> str | None:
        """Turn a year and a month into the first day of that month."""
        if not isinstance(value, dict) or not value.get("year"):
            return None
        return (
            f"{int(value['year']):04d}-{int(value.get('month') or 1):02d}-01"
        )

    @staticmethod
    def _moment(value: str | None) -> str | None:
        """Turn an exported timestamp into the format the index reads."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).isoformat()
        except ValueError:
            return None

    @staticmethod
    def _name(full_name: str | None) -> dict[str, str]:
        """Split a full name into the three parts the index keeps."""
        parts = (full_name or "").split()
        return {
            part: parts[position] if position < len(parts) else ""
            for position, part in enumerate(_NAME_PARTS)
        }

    @staticmethod
    def _salary(amount: Any) -> dict[str, Any] | None:
        """Return the wanted salary, in the only currency humart states."""
        if not isinstance(amount, int):
            return None
        return {"amount": amount, "currency": DEFAULT_CURRENCY}

    @staticmethod
    def _months(experience: list[dict[str, Any]]) -> int:
        """Return how many months of work the resume adds up to."""
        today = date.today()
        months = 0
        for entry in experience:
            if not entry["start"]:
                continue
            start = date.fromisoformat(entry["start"])
            end = date.fromisoformat(entry["end"]) if entry["end"] else today
            months += max(
                (end.year - start.year) * 12 + end.month - start.month,
                0,
            )
        return months

    @classmethod
    def _education(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """Return the schooling in the two groups the index keeps."""
        return {
            "primary": [
                {
                    "id": entry.get("id"),
                    "name": entry.get("name") or "",
                    "organization": entry.get("faculty") or "",
                    "result": entry.get("speciality") or "",
                    "year": cls._year(entry=entry),
                }
                for entry in raw.get("education") or []
                if isinstance(entry, dict)
            ],
            "additional": [
                {
                    "id": entry.get("id"),
                    "name": entry.get("name") or "",
                    "organization": entry.get("organization") or "",
                    "result": entry.get("certificate") or "",
                    "year": cls._year(entry=entry),
                }
                for entry in raw.get("additional_education") or []
                if isinstance(entry, dict)
            ],
        }

    @staticmethod
    def _year(entry: dict[str, Any]) -> int | None:
        """Return the year a place of study is dated by, if it is."""
        return (entry.get("dateObject") or {}).get("year")

    @staticmethod
    def _language(entry: dict[str, Any]) -> dict[str, Any]:
        """Return one language in the shape the index expects."""
        return {
            "id": entry.get("code"),
            "name": entry.get("name") or "",
            "level": {"name": entry.get("level") or ""},
        }
