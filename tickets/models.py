from django.conf import settings
from django.db import models

from cash.models import CashDay
from catalog.models import Extra, Service

# this where we are going to save the customer's data
class Customer(models.Model):
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        if self.full_name:
            return self.full_name
        return "Customer without name"

# This is the principal Ticket table
class Ticket(models.Model):
    WASH = "wash"
    PARKING = "parking"
    # each ticket has 1 type wash or parking
    TICKET_TYPE_CHOICES = [
        (WASH, "Wash"),
        (PARKING, "Parking"),
    ]
# this are the ticket status
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    PAID = "paid"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (PENDING_PAYMENT, "Pending payment"),
        (ACTIVE, "Active"),
        (PAID, "Paid"),
        (CANCELLED, "Cancelled"),
    ]

    ticket_number = models.CharField(
        max_length=30,
        unique=True,
    )

    ticket_type = models.CharField(
        max_length=30,
        choices=TICKET_TYPE_CHOICES,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tickets",
    )
# we connect our ticket with the service requested
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="tickets",
    )
# we connect our ticket with the cash day
    cash_day = models.ForeignKey(
        CashDay,
        on_delete=models.PROTECT,
        related_name="tickets",
    )

    customer_name_snapshot = models.CharField(max_length=150, blank=True)
    customer_phone_snapshot = models.CharField(max_length=30, blank=True)

    vehicle_plate = models.CharField(max_length=30)

    service_name_snapshot = models.CharField(max_length=120)
    service_price_with_tax_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    subtotal_without_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.13,
    )

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    total_with_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
# here we save the hash code that will be necessary to close the ticket
    closing_code_hash = models.TextField()

    parking_entry_at = models.DateTimeField(null=True, blank=True)
    parking_exit_at = models.DateTimeField(null=True, blank=True)
    parking_minutes = models.PositiveIntegerField(null=True, blank=True)

# from here we have the parking fields, so if the ticket is a parking type this will be use and the wash fields are going to be null

    parking_first_hour_price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    parking_block_price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    parking_block_minutes_snapshot = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    created_by_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tickets",
    )

    updated_by_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="updated_tickets",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_number} - {self.vehicle_plate}"


class TicketExtra(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="ticket_extras",
    )
# we connect our ticket with the extras
    extra = models.ForeignKey(
        Extra,
        on_delete=models.PROTECT,
        related_name="ticket_extras",
    )

    extra_name_snapshot = models.CharField(max_length=120)

    extra_price_with_tax_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    tax_rate_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.13,
    )

    subtotal_without_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    total_with_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.ticket.ticket_number} - {self.extra_name_snapshot}"