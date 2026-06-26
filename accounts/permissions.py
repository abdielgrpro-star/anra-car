from accounts.models import Role


def user_has_role(user, role_name):
    return (
        user.is_authenticated
        and user.role is not None
        and user.role.name == role_name
    )


def user_is_cashier(user):
    return user_has_role(user, Role.CASHIER)


def user_is_admin(user):
    return user_has_role(user, Role.ADMIN)


def user_is_technical_admin(user):
    return user_has_role(user, Role.TECHNICAL_ADMIN)


def user_can_authorize_sensitive_actions(user):
    return user_is_admin(user) or user_is_technical_admin(user) or user.is_superuser


def user_requires_otp_for_sensitive_actions(user):
    return not user_can_authorize_sensitive_actions(user)