from django.contrib.auth.hashers import check_password

from accounts.otp import set_new_otp_for_employee
from accounts.permissions import user_requires_otp_for_sensitive_actions
from audit.models import OtpUsage


def validate_sensitive_action_authorization(
    *,
    used_by_employee,
    authorized_by_employee,
    ticket,
    action_type,
    otp_code,
    reason,
):
    """
    Cashier:
        Requires OTP from admin/technical admin.
        Creates OtpUsage.
        If OTP is valid, rotates the admin OTP automatically.

    Admin / Technical Admin / Superuser:
        Does not require OTP.
        Does not create OtpUsage.
    """

    if not user_requires_otp_for_sensitive_actions(used_by_employee):
        return True, None, used_by_employee

    is_valid = False

    if authorized_by_employee and authorized_by_employee.otp_secret:
        is_valid = check_password(
            otp_code,
            authorized_by_employee.otp_secret,
        )

    otp_usage = OtpUsage.objects.create(
        used_by_employee=used_by_employee,
        authorized_by_employee=authorized_by_employee,
        ticket=ticket,
        action_type=action_type,
        reason=reason,
        was_valid=is_valid,
    )

    if is_valid and authorized_by_employee:
        set_new_otp_for_employee(
            authorized_by_employee,
            send_email=True,
        )

    return is_valid, otp_usage, authorized_by_employee