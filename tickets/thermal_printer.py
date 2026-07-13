import win32print
from django.utils import timezone
from django.conf import settings

PRINTER_NAME = getattr(settings, "THERMAL_PRINTER_NAME", "SAT 22TUS")


def send_raw_to_printer(raw_data, printer_name=PRINTER_NAME):
    printer = win32print.OpenPrinter(printer_name)

    try:
        win32print.StartDocPrinter(
            printer,
            1,
            ("Ticket ANRA", None, "RAW"),
        )

        try:
            win32print.StartPagePrinter(printer)
            win32print.WritePrinter(printer, raw_data)
            win32print.EndPagePrinter(printer)
        finally:
            win32print.EndDocPrinter(printer)

    finally:
        win32print.ClosePrinter(printer)


def encode_text(text):
    if text is None:
        text = ""

    return str(text).encode("cp850", errors="replace")


def format_local_datetime(value):
    if not value:
        return "No indicado"

    local_value = timezone.localtime(value)
    return local_value.strftime("%d/%m/%Y %H:%M")


def format_duration_unit(unit):
    if unit == "days":
        return "dia(s)"

    if unit == "weeks":
        return "semana(s)"

    if unit == "months":
        return "mes(es)"

    return unit or "No indicado"


def build_basic_ticket(ticket):
    ESC = b"\x1b"
    GS = b"\x1d"

    data = b""

    # Inicializar impresora
    data += ESC + b"@"

    # Centrar
    data += ESC + b"a" + b"\x01"

    # Negrita
    data += ESC + b"E" + b"\x01"
    data += encode_text("LAVACAR Y PARQUEO\n")
    data += encode_text("ANRA\n")
    data += ESC + b"E" + b"\x00"

    data += b"------------------------------\n"

    if ticket.ticket_type == "wash":
        data += encode_text("Ticket de lavado\n")

    elif ticket.ticket_type == "parking" and ticket.parking_mode == "prepaid":
        data += ESC + b"E" + b"\x01"
        data += encode_text("Ticket de parqueo prepago\n")
        data += ESC + b"E" + b"\x00"

    elif ticket.ticket_type == "parking":
        data += encode_text("Ticket de parqueo\n")

    data += b"------------------------------\n"

    # Izquierda
    data += ESC + b"a" + b"\x00"

    data += encode_text(f"Ticket: {ticket.ticket_number}\n")
    data += encode_text(f"Estado: {ticket.get_status_display()}\n")
    data += encode_text(f"Fecha: {format_local_datetime(ticket.created_at)}\n")
    data += encode_text(f"Cajero: {ticket.created_by_employee}\n")

    data += b"------------------------------\n"

    data += encode_text(
        f"Cliente: {ticket.customer_name_snapshot or 'No indicado'}\n"
    )
    data += encode_text(
        f"Telefono: {ticket.customer_phone_snapshot or 'No indicado'}\n"
    )
    data += encode_text(f"Placa: {ticket.vehicle_plate}\n")

    data += b"------------------------------\n"

    if ticket.ticket_type == "wash":
        data += encode_text("SERVICIO\n")
        data += encode_text(f"{ticket.service_name_snapshot}\n")
        data += encode_text(
            f"Precio: CRC {ticket.service_price_with_tax_snapshot}\n"
        )

        ticket_extras = ticket.ticket_extras.all()

        if ticket_extras:
            data += b"------------------------------\n"
            data += encode_text("EXTRAS\n")

            for ticket_extra in ticket_extras:
                data += encode_text(
                    f"{ticket_extra.extra_name_snapshot}: "
                    f"CRC {ticket_extra.extra_price_with_tax_snapshot}\n"
                )
        else:
            data += encode_text("Extras: Sin extras\n")

    elif ticket.ticket_type == "parking" and ticket.parking_mode == "prepaid":
        data += ESC + b"E" + b"\x01"
        data += encode_text("PARQUEO PREPAGO\n")
        data += ESC + b"E" + b"\x00"

        data += encode_text(
            f"Plan: {ticket.prepaid_plan_name_snapshot or ticket.prepaid_description or 'No indicado'}\n"
        )

        if (
            ticket.prepaid_plan_duration_quantity_snapshot
            and ticket.prepaid_plan_duration_unit_snapshot
        ):
            duration_unit = format_duration_unit(
                ticket.prepaid_plan_duration_unit_snapshot
            )

            data += encode_text(
                f"Duracion: {ticket.prepaid_plan_duration_quantity_snapshot} {duration_unit}\n"
            )

        data += encode_text(
            f"Vigencia inicio: {format_local_datetime(ticket.prepaid_start_at)}\n"
        )
        data += encode_text(
            f"Vigencia fin: {format_local_datetime(ticket.prepaid_end_at)}\n"
        )

        data += encode_text(
            f"Precio plan: CRC {ticket.prepaid_plan_price_with_tax_snapshot or ticket.service_price_with_tax_snapshot}\n"
        )

        if ticket.status == "paid":
            data += encode_text("Pago: Cancelado\n")
        else:
            data += encode_text("Pago: Pendiente\n")

    elif ticket.ticket_type == "parking":
        data += encode_text("PARQUEO POR HORAS\n")

        if ticket.parking_entry_at:
            data += encode_text(
                f"Entrada: {format_local_datetime(ticket.parking_entry_at)}\n"
            )

        if ticket.parking_exit_at:
            data += encode_text(
                f"Salida: {format_local_datetime(ticket.parking_exit_at)}\n"
            )
            data += encode_text(
                f"Tiempo total: {ticket.parking_minutes} minutos\n"
            )
        else:
            data += encode_text(
                f"Tarifa: CRC {ticket.parking_first_hour_price_snapshot} por hora iniciada\n"
            )

    data += b"------------------------------\n"

    data += encode_text(f"Subtotal sin IVA: CRC {ticket.subtotal_without_tax}\n")
    data += encode_text(f"IVA: CRC {ticket.tax_amount}\n")

    if ticket.discount_amount and ticket.discount_amount != 0:
        data += encode_text(f"Descuento: CRC {ticket.discount_amount}\n")

    data += b"------------------------------\n"

    data += ESC + b"a" + b"\x01"

    if ticket.ticket_type == "parking" and ticket.parking_mode == "prepaid":
        if ticket.status != "paid":
            data += encode_text("Este parqueo prepago\n")
            data += encode_text("esta pendiente de pago.\n")
        else:
            data += encode_text("Parqueo prepago pagado.\n")

        data += ESC + b"E" + b"\x01"
        data += encode_text(f"TOTAL: CRC {ticket.total_with_tax}\n")
        data += ESC + b"E" + b"\x00"

    elif ticket.ticket_type == "parking" and ticket.status == "active":
        data += encode_text("El total final se actualiza\n")
        data += encode_text("al devolver el ticket.\n")

        data += ESC + b"E" + b"\x01"
        data += encode_text(f"TOTAL ACTUAL: CRC {ticket.total_with_tax}\n")
        data += ESC + b"E" + b"\x00"

    else:
        data += ESC + b"E" + b"\x01"
        data += encode_text(f"TOTAL: CRC {ticket.total_with_tax}\n")
        data += ESC + b"E" + b"\x00"

    data += b"------------------------------\n"

    # Código de cierre
    # Solo se imprime si el ticket todavía no está pagado.
    if ticket.status != "paid":
        data += ESC + b"a" + b"\x01"
        data += ESC + b"E" + b"\x01"
        data += encode_text("CODIGO DE CIERRE\n")

        if ticket.closing_code_for_print:
            data += encode_text(f"{ticket.closing_code_for_print}\n")
        else:
            data += encode_text("No disponible\n")

        data += ESC + b"E" + b"\x00"
        data += b"------------------------------\n"

    data += encode_text("Gracias por preferirnos.\n")
    data += encode_text("Cuidamos su vehiculo.\n")

    if ticket.ticket_type == "parking" and ticket.parking_mode == "prepaid":
        data += encode_text("Presente este ticket como\n")
        data += encode_text("comprobante de vigencia.\n")
    else:
        data += encode_text("Presente este ticket al pagar.\n")

    # Avanzar papel
    data += b"\n\n\n\n"

    # Corte parcial
    data += GS + b"V" + b"\x42" + b"\x00"

    return data


def print_ticket(ticket):
    raw_data = build_basic_ticket(ticket)
    send_raw_to_printer(raw_data)