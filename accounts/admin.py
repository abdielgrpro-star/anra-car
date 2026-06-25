from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Employee, Role

# Here are are going to be able to administer the roles and employees using the defaul /admin/ panel


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description")
    search_fields = ("name",)


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    model = Employee

    list_display = (
        "id",
        "username",
        "full_name",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "username",
        "full_name",
        "email",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Business information",
            {
                "fields": (
                    "full_name",
                    "role",
                    "otp_secret",
                    "otp_enabled",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Business information",
            {
                "fields": (
                    "full_name",
                    "role",
                    "otp_secret",
                    "otp_enabled",
                )
            },
        ),
    )