from typing import Any

from services.indexing.constants import (
    MACOS_DIRECTORY,
    MACOS_PREFIX,
    MAX_RESUMES,
    TOO_MANY_RESUMES,
)


def is_macos_shadow(name: str) -> bool:
    """Report whether an entry is the shadow copy a mac zips alongside."""
    if name.startswith(MACOS_DIRECTORY):
        return True
    return name.rsplit("/", maxsplit=1)[-1].startswith(MACOS_PREFIX)


def limit_resumes(
    resumes: list[dict[str, Any]],
    errors: list[str],
) -> list[dict[str, Any]]:
    """Cut an oversized upload down, saying so in the errors."""
    # A truncated upload has to say so, not look like a whole one.
    if len(resumes) > MAX_RESUMES:
        errors.append(TOO_MANY_RESUMES.format(len(resumes), MAX_RESUMES))
    return resumes[:MAX_RESUMES]
