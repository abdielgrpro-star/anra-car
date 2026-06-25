from django.contrib.auth.models import AbstractUser
from django.db import models

# This will save the roles of each user here suach as cashier, admin or technical_admin
class Role(models.Model):
    CASHIER = "cashier"
    ADMIN = "admin"
    TECHNICAL_ADMIN = "technical_admin"

    ROLE_CHOICES = [
        (CASHIER, "Cashier"),
        (ADMIN, "Admin"),
        (TECHNICAL_ADMIN, "Technical Admin"),
    ]

    name = models.CharField(
        max_length=50,
        unique=True,
        choices=ROLE_CHOICES,
    )
    description = models.TextField(blank=True)

    def __str__(self):
        return self.get_name_display()

# This will be for the users that is going to sign in the app, we are going to use AbstractUser to use the default tools of django
class Employee(AbstractUser):
    full_name = models.CharField(max_length=150)

    role = models.ForeignKey(
        Role,
        # models.PROTECT will avoid to delete a role if a user has the role that we are trying to delete
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employees",
    )

    otp_secret = models.TextField(blank=True)
    otp_enabled = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.full_name:
            return self.full_name
        return self.username

    @property
    def is_cashier(self):
        return self.role and self.role.name == Role.CASHIER

    @property
    def is_admin_user(self):
        return self.role and self.role.name == Role.ADMIN

    @property
    def is_technical_admin(self):
        return self.role and self.role.name == Role.TECHNICAL_ADMIN
