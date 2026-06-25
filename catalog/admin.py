from django.contrib import admin
from .models import Service, Extra

# here we are going to be able to use /admin/ to administer the services and extras
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "service_type",
        "price_with_tax",
        "tax_rate",
        "is_active",
        "created_at",
    )

    list_filter = (
        "service_type",
        "is_active",
    )

    search_fields = (
        "name",
    )


@admin.register(Extra)
class ExtraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price_with_tax",
        "tax_rate",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )