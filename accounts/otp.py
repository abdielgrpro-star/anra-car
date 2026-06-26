import secrets

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.utils import timezone


def generate_otp_code():
    """
    Genera un OTP numérico de 6 dígitos.
    """
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


def set_new_otp_for_employee(employee, *, send_email=True):
    """
    Genera un nuevo OTP para un admin o admin técnico.

    Guarda:
    - otp_current_code visible
    - otp_secret hasheado para validación
    - otp_generated_at
    """

    new_code = generate_otp_code()

    employee.otp_current_code = new_code
    employee.otp_secret = make_password(new_code)
    employee.otp_enabled = True
    employee.otp_generated_at = timezone.now()

    employee.save(
        update_fields=[
            "otp_current_code",
            "otp_secret",
            "otp_enabled",
            "otp_generated_at",
            "updated_at",
        ]
    )

    email_sent = False

    if send_email and employee.email:
        subject = "Nuevo OTP de Anracar"

        message = (
            f"Hola {employee.full_name or employee.username},\n\n"
            f"Tu nuevo OTP para autorizar acciones en Anracar es:\n\n"
            f"{new_code}\n\n"
            f"Este código reemplaza el OTP anterior.\n"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[employee.email],
            fail_silently=True,
        )

        email_sent = True

    return new_code, email_sent