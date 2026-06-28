from django.conf import settings
from django.db import models

from cash.models import CashDay
from tickets.models import Ticket


class Payment(models.Model):
    CASH = "cash"
    SINPE = "sinpe"

    PAYMENT_METHOD_CHOICES = [
        (CASH, "Efectivo"),
        (SINPE, "SINPE"),
    ]
# this will connect the payment with an specific ticket
# we use OneToOneFiled because the ticket can have only 1 payment
    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.PROTECT,
        related_name="payment",
    )
# this will connect the payments with the cash day
    cash_day = models.ForeignKey(
        CashDay,
        on_delete=models.PROTECT,
        related_name="payments",
    )
# this will save which employee made the collection
    received_by_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_payments",
    )
# the method of payment (sinpe/cash)
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
    )
# total amount of the payment
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
# sinpe movil reference(this will be optional)
    sinpe_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment for {self.ticket.ticket_number} - ₡{self.amount}"