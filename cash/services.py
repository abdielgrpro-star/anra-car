from datetime import time

from django.db import transaction
from django.utils import timezone

from cash.models import CashDay


AUTO_OPEN_TIME = time(7, 0)
AUTO_CLOSE_TIME = time(20, 0)


def is_after_auto_close_time():
    return timezone.localtime().time() >= AUTO_CLOSE_TIME


def automatic_close_message():
    return (
        "El cierre de caja automático ya fue efectuado. "
        "Ya no se pueden crear ni cobrar tickets por hoy"
    )



@transaction.atomic
def close_today_cash_day_automatically_if_needed():
    today = timezone.localdate()

    cash_day = CashDay.objects.filter(
        business_date=today,
        status=CashDay.OPEN,
    ).first()

    if cash_day and is_after_auto_close_time():
        cash_day.status = CashDay.CLOSED
        cash_day.closed_at = timezone.now()
        cash_day.closed_automatically = True
        cash_day.save(
            update_fields=[
                "status",
                "closed_at",
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
    today = timezone.localdate()

    close_today_cash_day_automatically_if_needed()

    cash_day, created = CashDay.objects.get_or_create(
        business_date=today,
        defaults={
            "status": CashDay.OPEN,
            "opened_at": timezone.now(),
            "closed_automatically": False,
        },
    )

    # Si ya pasó la hora de cierre automático, no permitimos operar.
    if is_after_auto_close_time():
        if cash_day.status != CashDay.CLOSED or not cash_day.closed_automatically:
            cash_day.status = CashDay.CLOSED
            cash_day.closed_at = timezone.now()
            cash_day.closed_automatically = True
            cash_day.save(
                update_fields=[
                    "status",
                    "closed_at",
                    "closed_automatically",
                    "updated_at",
                ]
            )

        return cash_day

    # Si está cerrada manualmente antes de las 9:00 pm, sí se puede reabrir.
    if cash_day.status == CashDay.CLOSED and not cash_day.closed_automatically:
        cash_day.status = CashDay.OPEN
        cash_day.closed_at = None
        cash_day.closed_automatically = False
        cash_day.save(
            update_fields=[
                "status",
                "closed_at",
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

def cash_day_allows_operations(cash_day):
    if not cash_day:
        return False

    if cash_day.status != CashDay.OPEN:
        return False

    if is_after_auto_close_time():
        return False

    return True