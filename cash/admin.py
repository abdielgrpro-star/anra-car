from django.contrib import admin

from .models import CashDay

# with the default /admin/ we are going to see the actual cash day status
@admin.register(CashDay)
class CashDayAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business_date",
        "status",
        "opened_at",
        "closed_at",
        "closed_by_employee",
    )

    list_filter = (
        "status",
        "business_date",
    )

    search_fields = (
        "business_date",
    )