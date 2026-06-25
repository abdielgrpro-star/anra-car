from django.contrib import admin

from .models import Customer, Ticket, TicketExtra

# we will administer the tickets in the /admin/ page
class TicketExtraInline(admin.TabularInline):
    model = TicketExtra
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "phone",
        "created_at",
    )

    search_fields = (
        "full_name",
        "phone",
    )


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ticket_number",
        "ticket_type",
        "status",
        "vehicle_plate",
        "service_name_snapshot",
        "total_with_tax",
        "cash_day",
        "created_by_employee",
        "created_at",
    )

    list_filter = (
        "ticket_type",
        "status",
        "cash_day",
        "created_at",
    )

    search_fields = (
        "ticket_number",
        "vehicle_plate",
        "customer_name_snapshot",
        "customer_phone_snapshot",
    )

    inlines = [
        TicketExtraInline,
    ]


@admin.register(TicketExtra)
class TicketExtraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ticket",
        "extra_name_snapshot",
        "extra_price_with_tax_snapshot",
        "created_at",
    )

    search_fields = (
        "ticket__ticket_number",
        "extra_name_snapshot",
    )