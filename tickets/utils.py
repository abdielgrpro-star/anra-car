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