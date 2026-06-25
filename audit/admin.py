from django.contrib import admin

from .models import AuditLog, OtpUsage


@admin.register(OtpUsage)
class OtpUsageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action_type",
        "ticket",
        "used_by_employee",
        "authorized_by_employee",
        "was_valid",
        "used_at",
    )

    list_filter = (
        "action_type",
        "was_valid",
        "used_at",
    )

    search_fields = (
        "ticket__ticket_number",
        "used_by_employee__username",
        "authorized_by_employee__username",
        "reason",
    )

    readonly_fields = (
        "used_at",
        "created_at",
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action_type",
        "employee",
        "ticket",
        "otp_usage",
        "entity_type",
        "entity_id",
        "created_at",
    )

    list_filter = (
        "action_type",
        "entity_type",
        "created_at",
    )

    search_fields = (
        "ticket__ticket_number",
        "employee__username",
        "reason",
    )

    readonly_fields = (
        "created_at",
    )