from http import HTTPStatus
from typing import final

from services.api.common.exceptions import BaseAPIError
from services.api.resumes.constants import (
    EMPTY_UPLOAD,
    UNKNOWN_UPLOAD,
    UNREADABLE_UPLOAD,
    UPLOAD_FIELD,
)


@final
class UnreadableUploadError(BaseAPIError):
    """Report an upload that opens neither as a zip nor as JSON."""

    message = UNREADABLE_UPLOAD
    loc = UPLOAD_FIELD


@final
class EmptyUploadError(BaseAPIError):
    """Report an upload holding no resumes at all."""

    message = EMPTY_UPLOAD
    loc = UPLOAD_FIELD


@final
class UnknownUploadError(BaseAPIError):
    """Report a status request for an upload nobody made."""

    message = UNKNOWN_UPLOAD
    loc = "uploadId"
    status_code = HTTPStatus.NOT_FOUND
