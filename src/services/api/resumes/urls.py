from dmr.routing import Router, path

from services.api.resumes.controllers import (
    ResumeDashboardController,
    ResumePlanPageController,
    ResumeSearchController,
    ResumeSearchPageController,
    ResumeUploadController,
    ResumeUploadStatusController,
)

router = Router(
    prefix="resumes/",
    urls=[
        path("", ResumeSearchPageController.as_view(), name="page"),
        path("plan/", ResumePlanPageController.as_view(), name="plan"),
        path("search/", ResumeSearchController.as_view(), name="search"),
        path(
            "dashboard/",
            ResumeDashboardController.as_view(),
            name="dashboard",
        ),
        path("upload/", ResumeUploadController.as_view(), name="upload"),
        path(
            "upload/<uuid:upload_id>/",
            ResumeUploadStatusController.as_view(),
            name="upload-status",
        ),
    ],
)
