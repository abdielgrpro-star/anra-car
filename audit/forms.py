from django import forms

from accounts.models import Employee, Role
from accounts.permissions import user_requires_otp_for_sensitive_actions


class OtpAuthorizationForm(forms.Form):
    authorized_by_employee = forms.ModelChoiceField(
        label="Admin que autoriza",
        queryset=Employee.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    otp_code = forms.CharField(
        label="Código OTP",
        max_length=30,
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Ingrese el OTP del admin",
            "autocomplete": "off",
        }),
    )

    reason = forms.CharField(
        label="Motivo",
        required=True,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Explique por qué se requiere esta acción",
        }),
    )

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)

        super().__init__(*args, **kwargs)

        self.requires_otp = True

        if self.request_user:
            self.requires_otp = user_requires_otp_for_sensitive_actions(
                self.request_user
            )

        if self.requires_otp:
            self.fields["authorized_by_employee"].required = True
            self.fields["otp_code"].required = True
            self.fields["reason"].required = True

            self.fields["authorized_by_employee"].queryset = Employee.objects.filter(
                is_active=True,
                otp_enabled=True,
                role__name__in=[
                    Role.ADMIN,
                    Role.TECHNICAL_ADMIN,
                ],
            ).order_by("username")
        else:
            self.fields.pop("authorized_by_employee")
            self.fields.pop("otp_code")

            self.fields["reason"].required = False
            self.fields["reason"].widget.attrs["placeholder"] = (
                "Motivo opcional para dejar registro en auditoría"
            )