from django import forms
from audit.forms import OtpAuthorizationForm
from catalog.models import Extra, Service


class WashTicketForm(forms.Form):
    customer_name = forms.CharField(
        label="Nombre del cliente",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: Juan Pérez",
        }),
    )

    customer_phone = forms.CharField(
        label="Teléfono",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: 8888-8888",
        }),
    )

    vehicle_plate = forms.CharField(
        label="Placa",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: ABC123",
        }),
    )

    service = forms.ModelChoiceField(
        label="Tipo de lavado",
        queryset=Service.objects.none(),
        required=True,
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    extras = forms.ModelMultipleChoiceField(
        label="Extras",
        queryset=Extra.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["service"].queryset = Service.objects.filter(
            service_type=Service.WASH,
            is_active=True,
        )

        self.fields["extras"].queryset = Extra.objects.filter(
            is_active=True,
        )


class ChargeWashTicketForm(forms.Form):
    CASH = "cash"
    SINPE = "sinpe"

    PAYMENT_METHOD_CHOICES = [
        (CASH, "Efectivo"),
        (SINPE, "SINPE"),
    ]

    closing_code = forms.CharField(
        label="Código de cierre",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: K7M9-Q2XA-P4R8",
            "autocomplete": "off",
        }),
    )

    payment_method = forms.ChoiceField(
        label="Método de pago",
        choices=PAYMENT_METHOD_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    sinpe_reference = forms.CharField(
        label="Referencia SINPE",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Opcional",
        }),
    )

class ParkingTicketForm(forms.Form):
    customer_name = forms.CharField(
        label="Nombre del cliente",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: Juan Pérez",
        }),
    )

    customer_phone = forms.CharField(
        label="Teléfono",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: 8888-8888",
        }),
    )

    vehicle_plate = forms.CharField(
        label="Placa",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: ABC123",
        }),
    )

class ChargeParkingTicketForm(forms.Form):
    CASH = "cash"
    SINPE = "sinpe"

    PAYMENT_METHOD_CHOICES = [
        (CASH, "Efectivo"),
        (SINPE, "SINPE"),
    ]

    closing_code = forms.CharField(
        label="Código de cierre",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: K7M9-Q2XA-P4R8",
            "autocomplete": "off",
        }),
    )

    payment_method = forms.ChoiceField(
        label="Método de pago",
        choices=PAYMENT_METHOD_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    sinpe_reference = forms.CharField(
        label="Referencia SINPE",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Opcional",
        }),
    )


class ChargeWithoutCodeForm(OtpAuthorizationForm):
    CASH = "cash"
    SINPE = "sinpe"

    PAYMENT_METHOD_CHOICES = [
        (CASH, "Efectivo"),
        (SINPE, "SINPE"),
    ]

    payment_method = forms.ChoiceField(
        label="Método de pago",
        choices=PAYMENT_METHOD_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    sinpe_reference = forms.CharField(
        label="Referencia SINPE",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Opcional",
        }),
    )

class CancelTicketForm(OtpAuthorizationForm):
    pass

class ReprintTicketForm(OtpAuthorizationForm):
    pass