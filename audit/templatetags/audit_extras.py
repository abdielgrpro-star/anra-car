import json

from django import template

register = template.Library()


KEY_TRANSLATIONS = {
    "status": "Estado",
    "ticket_type": "Tipo de ticket",
    "customer_name": "Cliente",
    "customer_phone": "Teléfono",
    "vehicle_plate": "Placa",
    "ticket_number": "Número de ticket",
    "total_with_tax": "Total con IVA",
    "subtotal_without_tax": "Subtotal sin IVA",
    "tax_amount": "IVA",
    "discount_amount": "Descuento",
    "service": "Servicio",
    "extras": "Extras",
    "name": "Nombre",
    "price_with_tax": "Precio con IVA",
    "payment": "Pago",
    "method": "Método",
    "amount": "Monto",
    "sinpe_reference": "Referencia SINPE",
    "cash_day": "Caja",
    "paid_at": "Fecha de pago",
    "created_at": "Fecha de creación",
    "updated_at": "Fecha de actualización",
    "parking_entry_at": "Entrada de parqueo",
    "parking_exit_at": "Salida de parqueo",
    "parking_minutes": "Minutos de parqueo",
    "authorized_by_employee": "Autorizado por",
    "reason": "Motivo",
}


VALUE_TRANSLATIONS = {
    "wash": "Lavado",
    "parking": "Parqueo",
    "pending_payment": "Pendiente de pago",
    "active": "Activo",
    "paid": "Pagado",
    "cancelled": "Anulado",
    "cash": "Efectivo",
    "sinpe": "SINPE",
    "create_wash_ticket": "Crear ticket de lavado",
    "create_parking_ticket": "Crear ticket de parqueo",
    "charge_wash_ticket": "Cobrar ticket de lavado",
    "charge_parking_ticket": "Cobrar ticket de parqueo",
    "edit_ticket": "Editar ticket",
    "apply_discount": "Aplicar descuento",
    "cancel_ticket": "Anular ticket",
    "reprint_ticket": "Reimprimir ticket",
    "close_without_code": "Cerrar sin código",
    "reopen_ticket": "Reabrir ticket",
}


def translate_json_value(value):
    if isinstance(value, dict):
        translated = {}

        for key, item in value.items():
            translated_key = KEY_TRANSLATIONS.get(key, key)
            translated[translated_key] = translate_json_value(item)

        return translated

    if isinstance(value, list):
        return [translate_json_value(item) for item in value]

    if isinstance(value, str):
        return VALUE_TRANSLATIONS.get(value, value)

    return value


@register.filter
def pretty_json(value):
    if value is None:
        return "{}"

    try:
        translated_value = translate_json_value(value)

        return json.dumps(
            translated_value,
            indent=4,
            ensure_ascii=False,
            sort_keys=False,
        )
    except TypeError:
        return str(value)