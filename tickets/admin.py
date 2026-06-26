from django.contrib import admin

from tickets.models import Customer, Ticket, TicketExtra


class TicketExtraInline(admin.TabularInline):
    model = TicketExtra
    extra = 0

    readonly_fields = [
        "extra",
        "extra_name_snapshot",
        "extra_price_with_tax_snapshot",
        "tax_rate_snapshot",
        "subtotal_without_tax",
        "tax_amount",
        "total_with_tax",
        "created_at",
    ]

    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "full_name",
        "phone",
        "created_at",
    ]

    search_fields = [
        "full_name",
        "phone",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        "ticket_number",
        "ticket_type",
        "status",
        "vehicle_plate",
        "customer_name_snapshot",
        "total_with_tax",
        "cash_day",
        "created_by_employee",
        "created_at",
    ]

    list_filter = [
        "ticket_type",
        "status",
        "cash_day",
        "created_at",
    ]

    search_fields = [
        "ticket_number",
        "vehicle_plate",
        "customer_name_snapshot",
        "customer_phone_snapshot",
    ]

    readonly_fields = [
        "ticket_number",
        "ticket_type",
        "status",
        "customer",
        "service",
        "cash_day",
        "customer_name_snapshot",
        "customer_phone_snapshot",
        "vehicle_plate",
        "service_name_snapshot",
        "service_price_with_tax_snapshot",
        "subtotal_without_tax",
        "tax_rate",
        "tax_amount",
        "discount_amount",
        "total_with_tax",
        "closing_code_hash",
        "closing_code_for_print",
        "parking_entry_at",
        "parking_exit_at",
        "parking_minutes",
        "parking_first_hour_price_snapshot",
        "parking_block_price_snapshot",
        "parking_block_minutes_snapshot",
        "created_by_employee",
        "updated_by_employee",
        "created_at",
        "updated_at",
        "paid_at",
        "cancelled_at",
        "print_count",
        "last_printed_at",
        "last_printed_by_employee",
    ]

    inlines = [
        TicketExtraInline,
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TicketExtra)
class TicketExtraAdmin(admin.ModelAdmin):
    list_display = [
        "ticket",
        "extra_name_snapshot",
        "extra_price_with_tax_snapshot",
        "created_at",
    ]

    search_fields = [
        "ticket__ticket_number",
        "extra_name_snapshot",
    ]

    readonly_fields = [
        "ticket",
        "extra",
        "extra_name_snapshot",
        "extra_price_with_tax_snapshot",
        "tax_rate_snapshot",
        "subtotal_without_tax",
        "tax_amount",
        "total_with_tax",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False