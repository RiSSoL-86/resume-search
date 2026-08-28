import gzip
import json
import re
from pathlib import Path
from typing import Any, final

# Stored packed: the same directory takes 3 MB of disk and 0.5 MB of it.
DIRECTORY_PATH = Path(__file__).resolve().parent / "companies.json.gz"

# Legal forms and quotes say nothing about which company this is.
_LEGAL_FORMS = frozenset(
    {
        "ао",
        "зао",
        "ип",
        "нко",
        "оао",
        "ооо",
        "пао",
        "тоо",
        "фгуп",
        "гк",
        "group",
        "inc",
        "llc",
        "ltd",
    },
)
_PUNCTUATION_RE = re.compile(r"[^0-9a-zа-я]+")


@final
class CompanyDirectory:
    """Tell which company a name stands for and what it does for a living."""

    def __init__(self, path: Path = DIRECTORY_PATH) -> None:
        """Read the generated directory the export is matched against."""
        with gzip.open(path, mode="rt", encoding="utf-8") as directory_file:
            directory: dict[str, Any] = json.load(directory_file)
        self.companies: dict[str, dict[str, Any]] = directory["companies"]
        self.industries: dict[str, str] = directory["industries"]

    def lookup(self, name: str | None) -> dict[str, Any]:
        """Return the fields a known company adds to one job."""
        found = self.companies.get(self.normalize(name=name))
        if not found:
            return {}

        return {
            "company_id": found.get("id"),
            "industries": [
                {"id": industry, "name": self.industries.get(industry, "")}
                for industry in found.get("industries") or []
            ],
        }

    @staticmethod
    def normalize(name: str | None) -> str:
        """Return the key a company name is looked up by."""
        # "ООО «Сбер-Банк»" and "Сбер банк" have to meet somewhere.
        lowered = (name or "").casefold().replace("ё", "е")
        words = _PUNCTUATION_RE.sub(" ", lowered).split()
        kept = [word for word in words if word not in _LEGAL_FORMS]
        return " ".join(kept or words)
