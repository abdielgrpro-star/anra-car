from django import forms

from accounts.models import Employee, Role


class OtpAuthorizationForm(forms.Form):
    authorized_by_employee = forms.ModelChoiceField(
        label="Admin que autoriza",
        queryset=Employee.objects.none(),
        required=True,
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    otp_code = forms.CharField(
        label="Código OTP",
        max_length=30,
        required=True,
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
            "placeholder": "Explique por qué se requiere esta autorización",
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["authorized_by_employee"].queryset = Employee.objects.filter(
            is_active=True,
            otp_enabled=True,
            role__name__in=[
                Role.ADMIN,
                Role.TECHNICAL_ADMIN,
            ],
        ).order_by("username")