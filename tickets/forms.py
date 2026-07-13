from django import forms
from audit.forms import OtpAuthorizationForm, OtpAuthorizationForm
from accounts.permissions import user_requires_otp_for_sensitive_actions
from catalog.models import Extra, Service, PrepaidParkingPlan
from decimal import Decimal
from django.utils import timezone


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

class EditWashTicketForm(OtpAuthorizationForm):
    customer_name = forms.CharField(
        label="Nombre del cliente",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
        }),
    )

    customer_phone = forms.CharField(
        label="Teléfono",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
        }),
    )

    vehicle_plate = forms.CharField(
        label="Placa",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
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
        ticket = kwargs.pop("ticket", None)
        super().__init__(*args, **kwargs)

        self.fields["service"].queryset = Service.objects.filter(
            service_type=Service.WASH,
            is_active=True,
        )

        self.fields["extras"].queryset = Extra.objects.filter(
            is_active=True,
        )

        if ticket and not self.is_bound:
            self.fields["customer_name"].initial = ticket.customer_name_snapshot
            self.fields["customer_phone"].initial = ticket.customer_phone_snapshot
            self.fields["vehicle_plate"].initial = ticket.vehicle_plate
            self.fields["service"].initial = ticket.service

            self.fields["extras"].initial = [
                ticket_extra.extra
                for ticket_extra in ticket.ticket_extras.all()
            ]

class EditParkingTicketForm(OtpAuthorizationForm):
    customer_name = forms.CharField(
        label="Nombre del cliente",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
        }),
    )

    customer_phone = forms.CharField(
        label="Teléfono",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
        }),
    )

    vehicle_plate = forms.CharField(
        label="Placa",
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
        }),
    )

    prepaid_plan = forms.ModelChoiceField(
        label="Plan de parqueo prepago",
        queryset=PrepaidParkingPlan.objects.none(),
        required=False,
        empty_label="Seleccione un plan",
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
    )

    prepaid_start_at = forms.DateTimeField(
        label="Inicio de vigencia",
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={
            "class": "form-control",
            "type": "datetime-local",
        }),
    )

    def __init__(self, *args, **kwargs):
        ticket = kwargs.pop("ticket", None)
        super().__init__(*args, **kwargs)

        self.ticket = ticket

        if ticket:
            self.fields["customer_name"].initial = ticket.customer_name_snapshot
            self.fields["customer_phone"].initial = ticket.customer_phone_snapshot
            self.fields["vehicle_plate"].initial = ticket.vehicle_plate

            if ticket.parking_mode == ticket.PREPAID:
                self.fields["prepaid_plan"].queryset = (
                    PrepaidParkingPlan.objects
                    .filter(is_active=True)
                    .order_by("name")
                )

            if ticket.prepaid_start_at:
                local_prepaid_start_at = timezone.localtime(ticket.prepaid_start_at)

                self.fields["prepaid_start_at"].initial = (
                    local_prepaid_start_at.strftime("%Y-%m-%dT%H:%M")
                )

                current_plan = (
                    PrepaidParkingPlan.objects
                    .filter(
                        name=ticket.prepaid_plan_name_snapshot,
                        duration_quantity=ticket.prepaid_plan_duration_quantity_snapshot,
                        duration_unit=ticket.prepaid_plan_duration_unit_snapshot,
                        price_with_tax=ticket.prepaid_plan_price_with_tax_snapshot,
                    )
                    .first()
                )

                if current_plan:
                    self.fields["prepaid_plan"].initial = current_plan

            else:
                self.fields.pop("prepaid_plan")
                self.fields.pop("prepaid_start_at")

    def clean_vehicle_plate(self):
        vehicle_plate = self.cleaned_data.get("vehicle_plate", "")
        return vehicle_plate.strip().upper()

    def clean_customer_name(self):
        customer_name = self.cleaned_data.get("customer_name", "")
        return customer_name.strip()

    def clean_customer_phone(self):
        customer_phone = self.cleaned_data.get("customer_phone", "")
        return customer_phone.strip()

    def clean(self):
        cleaned_data = super().clean()

        if self.ticket and self.ticket.parking_mode == self.ticket.PREPAID:
            prepaid_plan = cleaned_data.get("prepaid_plan")
            prepaid_start_at = cleaned_data.get("prepaid_start_at")

            if not prepaid_plan:
                self.add_error(
                    "prepaid_plan",
                    "Debe seleccionar un plan de parqueo prepago.",
                )

            if not prepaid_start_at:
                self.add_error(
                    "prepaid_start_at",
                    "Debe ingresar el inicio de vigencia.",
                )

        return cleaned_data

class CancelTicketForm(OtpAuthorizationForm):
    pass

class ReprintTicketForm(OtpAuthorizationForm):
    pass

class ApplyDiscountForm(OtpAuthorizationForm):
    discount_amount = forms.DecimalField(
        label="Monto de descuento",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "0.01",
            "placeholder": "Ejemplo: 1000",
        }),
    )

    remove_discount = forms.BooleanField(
        label="Eliminar descuento",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
        }),
    )

    def __init__(self, *args, **kwargs):
        ticket = kwargs.pop("ticket", None)

        super().__init__(*args, **kwargs)

        if ticket and not self.is_bound:
            self.fields["discount_amount"].initial = ticket.discount_amount

    def clean(self):
        cleaned_data = super().clean()

        discount_amount = cleaned_data.get("discount_amount")
        remove_discount = cleaned_data.get("remove_discount")

        if remove_discount:
            cleaned_data["discount_amount"] = Decimal("0.00")
            return cleaned_data

        if discount_amount is None:
            self.add_error(
                "discount_amount",
                "Debe ingresar un monto de descuento.",
            )

        return cleaned_data
    
class PrepaidParkingTicketForm(forms.Form):
    customer_name = forms.CharField(
        label="Nombre del cliente",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ejemplo: Juan Pérez",
            }
        ),
    )

    customer_phone = forms.CharField(
        label="Teléfono",
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ejemplo: 8888-8888",
            }
        ),
    )

    vehicle_plate = forms.CharField(
        label="Placa",
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ejemplo: ABC123",
            }
        ),
    )

    prepaid_plan = forms.ModelChoiceField(
        label="Plan de parqueo prepago",
        queryset=PrepaidParkingPlan.objects.none(),
        required=True,
        empty_label="Seleccione un plan",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    prepaid_start_at = forms.DateTimeField(
        label="Inicio de vigencia",
        required=True,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={
                "class": "form-control",
                "type": "datetime-local",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["prepaid_plan"].queryset = (
            PrepaidParkingPlan.objects
            .filter(is_active=True)
            .order_by("name")
        )

        if not self.is_bound:
            now = timezone.localtime()
            self.fields["prepaid_start_at"].initial = now.strftime("%Y-%m-%dT%H:%M")

    def clean_vehicle_plate(self):
        vehicle_plate = self.cleaned_data.get("vehicle_plate", "")
        return vehicle_plate.strip().upper()

    def clean_customer_name(self):
        customer_name = self.cleaned_data.get("customer_name", "")
        return customer_name.strip()

    def clean_customer_phone(self):
        customer_phone = self.cleaned_data.get("customer_phone", "")
        return customer_phone.strip()