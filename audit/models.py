from django.conf import settings
from django.db import models

from tickets.models import Ticket

# this table is going to track actions
class OtpUsage(models.Model):
    REPRINT_TICKET = "reprint_ticket"
    EDIT_TICKET = "edit_ticket"
    APPLY_DISCOUNT = "apply_discount"
    CANCEL_TICKET = "cancel_ticket"
    CLOSE_WITHOUT_CODE = "close_without_code"

    ACTION_TYPE_CHOICES = [
        (REPRINT_TICKET, "Reprint ticket"),
        (EDIT_TICKET, "Edit ticket"),
        (APPLY_DISCOUNT, "Apply discount"),
        (CANCEL_TICKET, "Cancel ticket"),
        (CLOSE_WITHOUT_CODE, "Close without code"),
    ]

    used_by_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="used_otp_usages",
    )

    authorized_by_employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authorized_otp_usages",
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="otp_usages",
    )

    action_type = models.CharField(
        max_length=80,
        choices=ACTION_TYPE_CHOICES,
    )

    reason = models.TextField()

    was_valid = models.BooleanField(default=True)

    used_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-used_at"]

    def __str__(self):
        return f"{self.action_type} by {self.used_by_employee}"


class AuditLog(models.Model):
    LOGIN = "login"
    CREATE_WASH_TICKET = "create_wash_ticket"
    CREATE_PARKING_TICKET = "create_parking_ticket"
    CHARGE_WASH_TICKET = "charge_wash_ticket"
    CHARGE_PARKING_TICKET = "charge_parking_ticket"
    EDIT_CUSTOMER_DATA = "edit_customer_data"
    EDIT_TICKET = "edit_ticket"
    APPLY_DISCOUNT = "apply_discount"
    CANCEL_TICKET = "cancel_ticket"
    REPRINT_TICKET = "reprint_ticket"
    CLOSE_WITHOUT_CODE = "close_without_code"
    REOPEN_TICKET = "reopen_ticket"
    CHANGE_SERVICE_PRICE = "change_service_price"
    CHANGE_EXTRA_PRICE = "change_extra_price"
    CREATE_EMPLOYEE = "create_employee"
    DEACTIVATE_EMPLOYEE = "deactivate_employee"

    ACTION_TYPE_CHOICES = [
        (LOGIN, "Login"),
        (CREATE_WASH_TICKET, "Create wash ticket"),
        (CREATE_PARKING_TICKET, "Create parking ticket"),
        (CHARGE_WASH_TICKET, "Charge wash ticket"),
        (CHARGE_PARKING_TICKET, "Charge parking ticket"),
        (EDIT_CUSTOMER_DATA, "Edit customer data"),
        (EDIT_TICKET, "Edit ticket"),
        (APPLY_DISCOUNT, "Apply discount"),
        (CANCEL_TICKET, "Cancel ticket"),
        (REPRINT_TICKET, "Reprint ticket"),
        (CLOSE_WITHOUT_CODE, "Close without code"),
        (REOPEN_TICKET, "Reopen ticket"),
        (CHANGE_SERVICE_PRICE, "Change service price"),
        (CHANGE_EXTRA_PRICE, "Change extra price"),
        (CREATE_EMPLOYEE, "Create employee"),
        (DEACTIVATE_EMPLOYEE, "Deactivate employee"),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    otp_usage = models.ForeignKey(
        OtpUsage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action_type = models.CharField(
        max_length=80,
        choices=ACTION_TYPE_CHOICES,
    )

    entity_type = models.CharField(
        max_length=80,
        blank=True,
    )

    entity_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
# this will be use to save the previous data after editing a product
    old_values = models.JSONField(
        null=True,
        blank=True,
    )

    new_values = models.JSONField(
        null=True,
        blank=True,
    )

    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action_type} by {self.employee} at {self.created_at}"