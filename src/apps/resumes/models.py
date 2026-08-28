from typing import final, override

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimestampedAbstractModel, UUIDAbstractModel
from apps.common.services.file_uploadings import FileUploadService
from apps.resumes.choices import ResumeSource, UploadStatus


@final
class ResumeUpload(UUIDAbstractModel, TimestampedAbstractModel):
    """A file of resumes handed over to be indexed."""

    file = models.FileField(
        _("file"),
        upload_to=FileUploadService.prefix_based_upload_handler(
            "resume_uploads",
        ),
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=UploadStatus,
        default=UploadStatus.QUEUED,
    )
    indexed = models.PositiveIntegerField(_("indexed"), default=0)
    unchanged = models.PositiveIntegerField(_("unchanged"), default=0)
    skipped = models.PositiveIntegerField(_("skipped"), default=0)
    chunks = models.PositiveIntegerField(_("chunks"), default=0)
    sources = models.JSONField(_("sources"), default=dict, blank=True)
    errors = models.JSONField(_("errors"), default=list, blank=True)

    class Meta:
        """Name the model and order the uploads by recency."""

        verbose_name = _("resume upload")
        verbose_name_plural = _("resume uploads")
        ordering = ("-created_timestamp",)

    @override
    def __str__(self) -> str:
        """Return the upload as the admin lists it."""
        return f"{self.file.name} ({self.status})"


@final
class SearchPlan(UUIDAbstractModel, TimestampedAbstractModel):
    """One search, kept so its ranking can be re-weighted without rerunning."""

    vacancy = models.TextField(_("vacancy"))
    general = models.TextField(_("general requirements"), blank=True)
    recruiter = models.TextField(_("recruiter notes"), blank=True)
    filters = models.JSONField(_("filters"), default=dict)
    # The pool, scored per criterion and normalised. Moving a slider is a
    # weighted sum over this and nothing else, so it costs no query at all.
    matrix = models.JSONField(_("score matrix"), default=dict)
    # Where the recruiter left the sliders: what the extraction should learn.
    weights = models.JSONField(_("weights"), default=dict)
    total = models.PositiveIntegerField(_("total"), default=0)

    class Meta:
        """Name the model and order the plans by recency."""

        verbose_name = _("search plan")
        verbose_name_plural = _("search plans")
        ordering = ("-created_timestamp",)

    @override
    def __str__(self) -> str:
        """Return the plan as the admin lists it."""
        return f"{self.vacancy[:60]} ({self.total})"


@final
class IndexedResume(UUIDAbstractModel, TimestampedAbstractModel):
    """A resume already chunked, embedded and put into the index."""

    resume_id = models.CharField(_("resume ID"), max_length=64, unique=True)
    source = models.CharField(_("source"), max_length=16, choices=ResumeSource)
    # The hash of the resume, so an unchanged one is never embedded twice.
    fingerprint = models.CharField(_("fingerprint"), max_length=64)

    class Meta:
        """Name the model and order the resumes by recency."""

        verbose_name = _("indexed resume")
        verbose_name_plural = _("indexed resumes")
        ordering = ("-updated_timestamp",)

    @override
    def __str__(self) -> str:
        """Return the resume as the admin lists it."""
        return f"{self.resume_id} ({self.source})"
