from typing import final

from django.db import models
from django.utils.translation import gettext_lazy as _


@final
class UploadStatus(models.TextChoices):
    """List the states an uploaded file passes through."""

    QUEUED = "queued", _("queued")
    RUNNING = "running", _("running")
    INDEXED = "indexed", _("indexed")
    FAILED = "failed", _("failed")


@final
class ResumeSource(models.TextChoices):
    """List the systems resumes reach the index from."""

    HH = "hh", _("hh.ru")
    HUMART = "humart", _("humart")
