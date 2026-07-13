from django.db import models

# Here is the Service that will be used in the principal tickets


class Service(models.Model):
    WASH = "wash"
    PARKING = "parking"

    SERVICE_TYPE_CHOICES = [
        (WASH, "Wash"),
        (PARKING, "Parking"),
    ]

    name = models.CharField(max_length=120)

    service_type = models.CharField(
        max_length=30,
        choices=SERVICE_TYPE_CHOICES,
    )

    price_with_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.13,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["service_type", "name"]

    def __str__(self):
        return f"{self.name} - ₡{self.price_with_tax}"

# this is the extra service of the wash service type
class Extra(models.Model):
    name = models.CharField(max_length=120)

    price_with_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.13,
    )
    # is_active is used to avoid delete the extra or service when it is not going to be use anymore
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - ₡{self.price_with_tax}"
    
class PrepaidParkingPlan(models.Model):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"

    DURATION_UNIT_CHOICES = [
        (DAYS, "Día(s)"),
        (WEEKS, "Semana(s)"),
        (MONTHS, "Mes(es)"),
    ]

    name = models.CharField(max_length=120)

    duration_quantity = models.PositiveIntegerField(
        default=1,
    )

    duration_unit = models.CharField(
        max_length=20,
        choices=DURATION_UNIT_CHOICES,
    )

    price_with_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.13,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - ₡{self.price_with_tax}"