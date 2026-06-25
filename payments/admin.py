from django.contrib import admin

from .models import Payment

# This will help us to see the payments using the admin panel
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ticket",
        "amount",
        "payment_method",
        "cash_day",
        "received_by_employee",
        "created_at",
    )

    list_filter = (
        "payment_method",
        "cash_day",
        "created_at",
    )

    search_fields = (
        "ticket__ticket_number",
        "ticket__vehicle_plate",
        "sinpe_reference",
    )