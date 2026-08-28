from typing import final

from django.contrib import admin

from apps.resumes.models import IndexedResume, ResumeUpload


@final
class ResumeUploadAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Show what every upload did to the index."""

    list_display = (
        "id",
        "file",
        "status",
        "indexed",
        "unchanged",
        "skipped",
        "chunks",
        "created_timestamp",
    )
    list_filter = ("status",)
    readonly_fields = (
        "indexed",
        "unchanged",
        "skipped",
        "chunks",
        "sources",
        "errors",
    )


@final
class IndexedResumeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Show which resumes the index already holds."""

    list_display = ("resume_id", "source", "updated_timestamp")
    list_filter = ("source",)
    search_fields = ("resume_id",)
    readonly_fields = ("resume_id", "source", "fingerprint")


admin.site.register(ResumeUpload, ResumeUploadAdmin)
admin.site.register(IndexedResume, IndexedResumeAdmin)
