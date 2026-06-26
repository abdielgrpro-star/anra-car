from django.contrib import admin
from django.contrib.admin.sites import NotRegistered

from audit.models import AuditLog, OtpUsage


try:
    admin.site.unregister(OtpUsage)
except NotRegistered:
    pass


try:
    admin.site.unregister(AuditLog)
except NotRegistered:
    pass


@admin.register(OtpUsage)
class OtpUsageAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "used_by_employee",
        "authorized_by_employee",
        "ticket",
        "action_type",
        "was_valid",
        "reason",
        "used_at",
    ]

    list_filter = [
        "action_type",
        "was_valid",
        "used_at",
    ]

    search_fields = [
        "used_by_employee__username",
        "authorized_by_employee__username",
        "ticket__ticket_number",
        "reason",
    ]

    readonly_fields = [
        "used_by_employee",
        "authorized_by_employee",
        "ticket",
        "action_type",
        "reason",
        "was_valid",
        "used_at",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "employee",
        "ticket",
        "action_type",
        "entity_type",
        "entity_id",
        "reason",
        "created_at",
    ]

    list_filter = [
        "action_type",
        "created_at",
    ]

    search_fields = [
        "employee__username",
        "ticket__ticket_number",
        "reason",
        "entity_type",
    ]

    readonly_fields = [
        "employee",
        "ticket",
        "otp_usage",
        "action_type",
        "entity_type",
        "entity_id",
        "old_values",
        "new_values",
        "reason",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False