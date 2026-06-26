from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import Employee, Role
from accounts.otp import set_new_otp_for_employee


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "description",
    ]


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    actions = [
        "generate_new_otp",
    ]

    list_display = [
        "username",
        "full_name",
        "email",
        "role",
        "is_active",
        "otp_enabled",
        "otp_current_code",
        "otp_generated_at",
    ]

    fieldsets = UserAdmin.fieldsets + (
        (
            "Datos de Anracar",
            {
                "fields": (
                    "full_name",
                    "role",
                    "otp_enabled",
                    "otp_current_code",
                    "otp_generated_at",
                ),
            },
        ),
    )

    readonly_fields = [
        "otp_current_code",
        "otp_generated_at",
    ]

    def generate_new_otp(self, request, queryset):
        count = 0

        for employee in queryset:
            set_new_otp_for_employee(
                employee,
                send_email=True,
            )
            count += 1

        self.message_user(
            request,
            f"Se generó un nuevo OTP para {count} usuario(s).",
        )

    generate_new_otp.short_description = "Generar nuevo OTP y enviar por correo"