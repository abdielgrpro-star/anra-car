import secrets
import string
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from tickets.models import Ticket


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_tax_from_total(total_with_tax, tax_rate):
    total_with_tax = Decimal(total_with_tax)
    tax_rate = Decimal(tax_rate)

    subtotal_without_tax = total_with_tax / (Decimal("1.00") + tax_rate)
    tax_amount = total_with_tax - subtotal_without_tax

    return {
        "subtotal_without_tax": money(subtotal_without_tax),
        "tax_amount": money(tax_amount),
        "total_with_tax": money(total_with_tax),
    }


def generate_closing_code():
    alphabet = string.ascii_uppercase + string.digits
    part_1 = "".join(secrets.choice(alphabet) for _ in range(4))
    part_2 = "".join(secrets.choice(alphabet) for _ in range(4))
    part_3 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{part_1}-{part_2}-{part_3}"


def generate_ticket_number(prefix="L"):
    today = timezone.localdate()
    date_part = today.strftime("%Y%m%d")

    starts_with = f"{prefix}-{date_part}"

    last_ticket = Ticket.objects.filter(
        ticket_number__startswith=starts_with
    ).order_by("-id").first()

    if not last_ticket:
        next_number = 1
    else:
        last_sequence = int(last_ticket.ticket_number.split("-")[-1])
        next_number = last_sequence + 1

    return f"{prefix}-{date_part}-{next_number:04d}"

def calculate_parking_total(minutes, first_hour_price, block_price, block_minutes):
    minutes = int(minutes)
    first_hour_price = Decimal(first_hour_price)
    block_price = Decimal(block_price)
    block_minutes = int(block_minutes)

    if minutes <= 60:
        return money(first_hour_price)

    extra_minutes = minutes - 60

    # Bloques iniciados después de la primera hora
    extra_blocks = (extra_minutes // block_minutes) + 1

    total = first_hour_price + (Decimal(extra_blocks) * block_price)

    return money(total)

def calculate_current_parking_total(ticket):
    """
    Calcula el total actual de un ticket de parqueo activo.

    Regla:
    - 0 a 60 minutos: primera hora
    - 61 a 89 minutos: primera hora + 1 bloque
    - 90 a 119 minutos: primera hora + 2 bloques
    - etc.
    """

    if not ticket.parking_entry_at:
        return ticket.total_with_tax, 0

    now = timezone.now()

    minutes = int(
        (now - ticket.parking_entry_at).total_seconds() // 60
    )

    if minutes < 0:
        minutes = 0

    first_hour_price = (
        ticket.parking_first_hour_price_snapshot
        or Decimal("1000.00")
    )

    block_price = (
        ticket.parking_block_price_snapshot
        or Decimal("500.00")
    )

    block_minutes = ticket.parking_block_minutes_snapshot or 30

    if minutes <= 60:
        total = first_hour_price
    else:
        extra_blocks = ((minutes - 60) // block_minutes) + 1
        total = first_hour_price + (Decimal(extra_blocks) * block_price)

    return total, minutes



