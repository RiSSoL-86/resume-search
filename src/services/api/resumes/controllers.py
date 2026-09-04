from http import HTTPStatus
from typing import TYPE_CHECKING, cast, final

from django.http import HttpResponse
from dmr import (
    Body,
    Controller,
    FileMetadata,
    Path,
    ResponseSpec,
    modify,
    validate,
)
from dmr.parsers import FormUrlEncodedParser, MultiPartParser
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer

from services.api.resumes.constants import (
    FALLBACK,
    FORM_TEMPLATE,
    PLAN_TEMPLATE,
    TEMPLATE,
    UPLOAD_FIELD,
)
from services.api.resumes.schemas import (
    ResumePlanForm,
    ResumeSearchForm,
    ResumeSearchRequest,
    ResumeSearchResponse,
    ResumeUploadPath,
    ResumeUploadPayload,
    ResumeUploadStatus,
)
from services.api.resumes.services.dashboard import ResumeDashboardService
from services.api.resumes.services.plan import ResumePlanService
from services.api.resumes.services.search import ResumeSearchService
from services.api.resumes.services.upload import ResumeUploadService
from services.api.resumes.services.upload_status import (
    ResumeUploadStatusService,
)
from services.api.resumes.utils import render_html

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile


@final
class ResumeSearchController(Controller[PydanticSerializer]):
    """Search resumes by a free-form vacancy description."""

    auth = None

    @modify(status_code=HTTPStatus.OK, tags=["Resumes"])
    async def post(
        self,
        parsed_body: Body[ResumeSearchRequest],
    ) -> ResumeSearchResponse:
        """Return candidates ranked against the given requirements."""
        service = ResumeSearchService()
        return await service.execute(payload=parsed_body)


@final
class ResumeDashboardController(Controller[PydanticSerializer]):
    """Render the ranked candidates as resume pages instead of JSON."""

    auth = None

    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            limit_to_content_types={"text/html"},
            description="Ranked candidates rendered as HTML",
        ),
        tags=["Resumes"],
        renderers=[FileRenderer("text/html")],
        validate_responses=False,
    )
    async def post(
        self,
        parsed_body: Body[ResumeSearchRequest],
    ) -> HttpResponse:
        """Return the same ranking the search endpoint builds, as a page."""
        service = ResumeDashboardService()
        context = await service.execute(payload=parsed_body)
        return await render_html(
            status=HTTPStatus.OK,
            context={"dashboard": context},
            template_name=TEMPLATE,
            download_name=context.filters.role_query or FALLBACK,
        )


@final
class ResumePlanPageController(Controller[PydanticSerializer]):
    """Search on the criteria a recruiter has just gone over by hand."""

    auth = None
    parsers = (FormUrlEncodedParser(), MultiPartParser())

    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            limit_to_content_types={"text/html"},
            description="Ranked candidates rendered as HTML",
        ),
        tags=["Resumes"],
        renderers=[FileRenderer("text/html")],
        validate_responses=False,
    )
    async def post(
        self,
        parsed_body: Body[ResumePlanForm],
    ) -> HttpResponse:
        """Return the ranking the reviewed criteria produce."""
        payload = await ResumePlanService().reviewed(form=parsed_body)
        service = ResumeDashboardService()
        context = await service.execute(payload=payload)
        return await render_html(
            status=HTTPStatus.OK,
            context={"dashboard": context},
            template_name=TEMPLATE,
            request=self.request,
        )


@final
class ResumeUploadController(Controller[PydanticSerializer]):
    """Queue an uploaded zip archive or JSON file of resumes for indexing."""

    auth = None
    parsers = (MultiPartParser(),)

    @modify(status_code=HTTPStatus.ACCEPTED, tags=["Resumes"])
    async def post(
        self,
        parsed_file_metadata: FileMetadata[ResumeUploadPayload],
    ) -> ResumeUploadStatus:
        """Hand the file over to a worker and return the upload."""
        # The metadata is validated by now, so the file is there.
        file = cast("UploadedFile", self.request.FILES[UPLOAD_FIELD])
        service = ResumeUploadService()
        return await service.execute(file=file)


@final
class ResumeUploadStatusController(Controller[PydanticSerializer]):
    """Report what the worker made of one upload."""

    auth = None

    @modify(status_code=HTTPStatus.OK, tags=["Resumes"])
    async def get(
        self,
        parsed_path: Path[ResumeUploadPath],
    ) -> ResumeUploadStatus:
        """Return where the upload got to."""
        service = ResumeUploadStatusService()
        return await service.execute(upload_id=parsed_path.upload_id)


@final
class ResumeSearchPageController(Controller[PydanticSerializer]):
    """Serve the page a vacancy is searched from."""

    auth = None
    parsers = (FormUrlEncodedParser(), MultiPartParser())

    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            limit_to_content_types={"text/html"},
            description="The form a vacancy is typed into",
        ),
        tags=["Resumes"],
        renderers=[FileRenderer("text/html")],
        validate_responses=False,
    )
    async def get(self) -> HttpResponse:
        """Return the empty search form."""
        return await self._form(form=ResumeSearchForm())

    @validate(
        ResponseSpec(
            str,
            status_code=HTTPStatus.OK,
            limit_to_content_types={"text/html"},
            description="Ranked candidates rendered as HTML",
        ),
        tags=["Resumes"],
        renderers=[FileRenderer("text/html")],
        validate_responses=False,
    )
    async def post(
        self,
        parsed_body: Body[ResumeSearchForm],
    ) -> HttpResponse:
        """Return the criteria the texts were read into, before searching."""
        error = parsed_body.error()
        if error:
            return await self._form(form=parsed_body, error=error)

        service = ResumePlanService()
        plan = await service.execute(payload=parsed_body.to_request())
        return await render_html(
            status=HTTPStatus.OK,
            context={"plan": plan},
            template_name=PLAN_TEMPLATE,
            request=self.request,
        )

    async def _form(
        self,
        form: ResumeSearchForm,
        error: str = "",
    ) -> HttpResponse:
        """Return the search form as the visitor last left it."""
        return await render_html(
            status=HTTPStatus.OK,
            context={"form": form, "error": error},
            template_name=FORM_TEMPLATE,
            request=self.request,
        )
