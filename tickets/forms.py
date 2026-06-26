from django import forms

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