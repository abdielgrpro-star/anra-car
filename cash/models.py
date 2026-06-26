from django.conf import settings
from django.db import models


class CashDay(models.Model):
    OPEN = "open"
    CLOSED = "closed"

    STATUS_CHOICES = [
        (OPEN, "Open"),
        (CLOSED, "Closed"),
    ]

    business_date = models.DateField(unique=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=OPEN,
    )

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    closed_by_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_cash_days",
    )

    closed_automatically = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-business_date"]

    def __str__(self):
        return f"Cash day {self.business_date} - {self.status}"