from typing import final

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


@final
class ResumesConfig(AppConfig):
    """Configure the resumes application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.resumes"
    verbose_name = _("resumes")
