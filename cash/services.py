from datetime import time

from django.db import transaction
from django.utils import timezone

from cash.models import CashDay


AUTO_OPEN_TIME = time(7, 0)
AUTO_CLOSE_TIME = time(21, 0)


def is_after_auto_close_time():
    now = timezone.localtime()
    return now.time() >= AUTO_CLOSE_TIME


@transaction.atomic
def close_today_cash_day_automatically_if_needed():
    """
    Cierra la caja de hoy automáticamente si ya son las 9:00 pm o más.
    """
    if not is_after_auto_close_time():
        return None

    today = timezone.localdate()

    cash_day = CashDay.objects.filter(
        business_date=today,
        status=CashDay.OPEN,
    ).first()

    if not cash_day:
        return None

    now = timezone.now()

    cash_day.status = CashDay.CLOSED
    cash_day.closed_at = now
    cash_day.closed_by_employee = None
    cash_day.closed_automatically = True

    cash_day.save(
        update_fields=[
            "status",
            "closed_at",
            "closed_by_employee",
            "closed_automatically",
            "updated_at",
        ]
    )

    return cash_day


@transaction.atomic
def get_today_cash_day_for_view():
    """
    Devuelve la caja de hoy para verla en pantalla.

    Importante:
    - Si está cerrada, NO la reabre.
    - Solo la crea si no existe.
    - Si ya son las 9:00 pm, cierra automáticamente si estaba abierta.
    """
    close_today_cash_day_automatically_if_needed()

    today = timezone.localdate()

    cash_day, created = CashDay.objects.get_or_create(
        business_date=today,
        defaults={
            "status": CashDay.OPEN,
        },
    )

    return cash_day


@transaction.atomic
def get_or_create_today_cash_day_for_operation():
    """
    Devuelve la caja de hoy para operaciones como crear tickets.

    Si no existe, la crea.
    Si está cerrada y aún no son las 9:00 pm, la reabre.
    Si ya son las 9:00 pm o más, la deja cerrada.
    """
    close_today_cash_day_automatically_if_needed()

    today = timezone.localdate()

    cash_day, created = CashDay.objects.get_or_create(
        business_date=today,
        defaults={
            "status": CashDay.OPEN,
        },
    )

    if created:
        return cash_day

    if cash_day.status == CashDay.CLOSED and not is_after_auto_close_time():
        cash_day.status = CashDay.OPEN
        cash_day.closed_at = None
        cash_day.closed_by_employee = None
        cash_day.closed_automatically = False

        cash_day.save(
            update_fields=[
                "status",
                "closed_at",
                "closed_by_employee",
                "closed_automatically",
                "updated_at",
            ]
        )

    return cash_day


@transaction.atomic
def close_cash_day_manually(*, cash_day, closed_by_employee):
    """
    Cierra manualmente la caja del día.
    """
    if cash_day.status == CashDay.CLOSED:
        return cash_day

    cash_day.status = CashDay.CLOSED
    cash_day.closed_at = timezone.now()
    cash_day.closed_by_employee = closed_by_employee
    cash_day.closed_automatically = False

    cash_day.save(
        update_fields=[
            "status",
            "closed_at",
            "closed_by_employee",
            "closed_automatically",
            "updated_at",
        ]
    )

    return cash_day