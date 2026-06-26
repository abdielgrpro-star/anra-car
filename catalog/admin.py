from django.contrib import admin

from catalog.models import Extra, Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "service_type",
        "price_with_tax",
        "tax_rate",
        "is_active",
        "created_at",
        "updated_at",
    ]

    list_filter = [
        "service_type",
        "is_active",
    ]

    search_fields = [
        "name",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    actions = [
        "activate_services",
        "deactivate_services",
    ]

    def has_delete_permission(self, request, obj=None):
        return False

    def activate_services(self, request, queryset):
        queryset.update(is_active=True)

    activate_services.short_description = "Activar servicios seleccionados"

    def deactivate_services(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_services.short_description = "Desactivar servicios seleccionados"


@admin.register(Extra)
class ExtraAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "price_with_tax",
        "tax_rate",
        "is_active",
        "created_at",
        "updated_at",
    ]

    list_filter = [
        "is_active",
    ]

    search_fields = [
        "name",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    actions = [
        "activate_extras",
        "deactivate_extras",
    ]

    def has_delete_permission(self, request, obj=None):
        return False

    def activate_extras(self, request, queryset):
        queryset.update(is_active=True)

    activate_extras.short_description = "Activar extras seleccionados"

    def deactivate_extras(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_extras.short_description = "Desactivar extras seleccionados"