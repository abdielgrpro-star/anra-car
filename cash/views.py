import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date
from tickets.models import Ticket

from accounts.permissions import user_can_authorize_sensitive_actions
from cash.models import CashDay
from cash.services import get_today_cash_day_for_view, close_cash_day_manually
from payments.models import Payment

@login_required
def cash_day_detail(request):
    if not user_can_authorize_sensitive_actions(request.user):
        messages.error(
            request,
            "No tiene permisos para ver la caja del día.",
        )
        return redirect("home")

    cash_day = get_today_cash_day_for_view()

    payments = (
        Payment.objects
        .select_related("ticket", "received_by_employee")
        .filter(cash_day=cash_day)
        .order_by("-created_at")
    )

    cash_total = (
        payments
        .filter(payment_method=Payment.CASH)
        .aggregate(total=Sum("amount"))
        ["total"]
        or 0
    )

    sinpe_total = (
        payments
        .filter(payment_method=Payment.SINPE)
        .aggregate(total=Sum("amount"))
        ["total"]
        or 0
    )

    total_general = cash_total + sinpe_total

    tickets_today = Ticket.objects.filter(cash_day=cash_day)

    ticket_stats = tickets_today.aggregate(
        total_tickets=Count("id"),
    )

    paid_tickets_count = tickets_today.filter(status=Ticket.PAID).count()
    pending_tickets_count = tickets_today.filter(status=Ticket.PENDING_PAYMENT).count()
    active_tickets_count = tickets_today.filter(status=Ticket.ACTIVE).count()
    cancelled_tickets_count = tickets_today.filter(status=Ticket.CANCELLED).count()

    first_payment = payments.order_by("created_at").first()
    last_payment = payments.order_by("-created_at").first()

    return render(
        request,
        "cash/cash_day_detail.html",
        {
            "cash_day": cash_day,
            "payments": payments,
            "cash_total": cash_total,
            "sinpe_total": sinpe_total,
            "total_general": total_general,
            "ticket_stats": ticket_stats,
            "paid_tickets_count": paid_tickets_count,
            "pending_tickets_count": pending_tickets_count,
            "active_tickets_count": active_tickets_count,
            "cancelled_tickets_count": cancelled_tickets_count,
            "first_payment": first_payment,
            "last_payment": last_payment,
        },
    )

@login_required
def close_cash_day_confirm(request):
    if not user_can_authorize_sensitive_actions(request.user):
        messages.error(
            request,
            "No tiene permisos para cerrar caja.",
        )
        return redirect("home")

    cash_day = get_today_cash_day_for_view()

    if request.method == "POST":
        if cash_day.status == CashDay.CLOSED:
            messages.warning(
                request,
                "La caja del día ya está cerrada.",
            )
            return redirect("cash:cash_day_detail")

        close_cash_day_manually(
            cash_day=cash_day,
            closed_by_employee=request.user,
        )

        messages.success(
            request,
            "Caja del día cerrada correctamente.",
        )

        return redirect("cash:cash_day_detail")

    return render(
        request,
        "cash/close_cash_day_confirm.html",
        {
            "cash_day": cash_day,
        },
    )


def get_cash_day_summary(cash_day):
    payments = Payment.objects.filter(
        cash_day=cash_day,
    )

    cash_total = (
        payments
        .filter(payment_method=Payment.CASH)
        .aggregate(total=Sum("amount"))
        ["total"]
        or Decimal("0.00")
    )

    sinpe_total = (
        payments
        .filter(payment_method=Payment.SINPE)
        .aggregate(total=Sum("amount"))
        ["total"]
        or Decimal("0.00")
    )

    total_general = cash_total + sinpe_total

    tickets_count = payments.values("ticket").distinct().count()

    first_payment = payments.order_by("created_at").first()
    last_payment = payments.order_by("-created_at").first()

    return {
        "cash_day": cash_day,
        "cash_total": cash_total,
        "sinpe_total": sinpe_total,
        "total_general": total_general,
        "tickets_count": tickets_count,
        "first_payment": first_payment,
        "last_payment": last_payment,
    }

#reporte de 1 dia de caja listado
@login_required
def cash_day_report_list(request):
    if not user_can_authorize_sensitive_actions(request.user):
        messages.error(
            request,
            "No tiene permisos para ver reportes de caja.",
        )
        return redirect("home")

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    parsed_date_from = parse_date(date_from) if date_from else None
    parsed_date_to = parse_date(date_to) if date_to else None

    cash_days = CashDay.objects.all().order_by("-business_date")

    if parsed_date_from:
        cash_days = cash_days.filter(
            business_date__gte=parsed_date_from,
        )

    if parsed_date_to:
        cash_days = cash_days.filter(
            business_date__lte=parsed_date_to,
        )

    summaries = []

    total_cash = Decimal("0.00")
    total_sinpe = Decimal("0.00")
    total_general = Decimal("0.00")
    total_tickets = 0

    for cash_day in cash_days[:100]:
        summary = get_cash_day_summary(cash_day)

        summaries.append(summary)

        total_cash += summary["cash_total"]
        total_sinpe += summary["sinpe_total"]
        total_general += summary["total_general"]
        total_tickets += summary["tickets_count"]

    selected_cash_day = None
    selected_payments = None

    # Si el filtro es un solo día exacto, mostramos los tickets/pagos de esa caja.
    if parsed_date_from and parsed_date_to and parsed_date_from == parsed_date_to:
        selected_cash_day = CashDay.objects.filter(
            business_date=parsed_date_from,
        ).first()

        if selected_cash_day:
            selected_payments = (
                Payment.objects
                .select_related(
                    "ticket",
                    "received_by_employee",
                )
                .filter(cash_day=selected_cash_day)
                .order_by("created_at")
            )

    return render(
        request,
        "cash/cash_day_report_list.html",
        {
            "date_from": date_from,
            "date_to": date_to,
            "summaries": summaries,
            "total_cash": total_cash,
            "total_sinpe": total_sinpe,
            "total_general": total_general,
            "total_tickets": total_tickets,
            "selected_cash_day": selected_cash_day,
            "selected_payments": selected_payments,
            "result_limit": 100,
        },
    )

#exporta el reporte del dia en csv
@login_required
def cash_day_report_export_csv(request):
    if not user_can_authorize_sensitive_actions(request.user):
        messages.error(
            request,
            "No tiene permisos para exportar reportes de caja.",
        )
        return redirect("home")

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    parsed_date_from = parse_date(date_from) if date_from else None
    parsed_date_to = parse_date(date_to) if date_to else None

    cash_days = CashDay.objects.all().order_by("business_date")

    if parsed_date_from:
        cash_days = cash_days.filter(
            business_date__gte=parsed_date_from,
        )

    if parsed_date_to:
        cash_days = cash_days.filter(
            business_date__lte=parsed_date_to,
        )

    response = HttpResponse(
        content_type="text/csv",
    )

    response["Content-Disposition"] = (
        'attachment; filename="reporte_cajas.csv"'
    )

    writer = csv.writer(response)

    # Si es un solo día, exportamos detalle de tickets/pagos.
    if parsed_date_from and parsed_date_to and parsed_date_from == parsed_date_to:
        cash_day = CashDay.objects.filter(
            business_date=parsed_date_from,
        ).first()

        writer.writerow([
            "Reporte de caja",
            parsed_date_from,
        ])

        writer.writerow([])

        if not cash_day:
            writer.writerow([
                "No existe caja para esa fecha.",
            ])
            return response

        summary = get_cash_day_summary(cash_day)

        writer.writerow([
            "Fecha",
            "Total efectivo",
            "Total SINPE",
            "Total general",
            "Total tickets cobrados",
        ])

        writer.writerow([
            cash_day.business_date,
            summary["cash_total"],
            summary["sinpe_total"],
            summary["total_general"],
            summary["tickets_count"],
        ])

        writer.writerow([])
        writer.writerow([
            "Hora de cobro",
            "Ticket",
            "Tipo",
            "Estado",
            "Placa",
            "Cliente",
            "Metodo de pago",
            "Monto",
            "Referencia SINPE",
            "Cobrado por",
        ])

        payments = (
            Payment.objects
            .select_related(
                "ticket",
                "received_by_employee",
            )
            .filter(cash_day=cash_day)
            .order_by("created_at")
        )

        for payment in payments:
            ticket = payment.ticket

            writer.writerow([
                payment.created_at.strftime("%d/%m/%Y %H:%M"),
                ticket.ticket_number,
                ticket.get_ticket_type_display(),
                ticket.get_status_display(),
                ticket.vehicle_plate,
                ticket.customer_name_snapshot,
                payment.get_payment_method_display(),
                payment.amount,
                payment.sinpe_reference,
                payment.received_by_employee.username,
            ])

        return response

    # Si es rango, exportamos resumen de cajas.
    writer.writerow([
        "Reporte de cajas",
    ])

    writer.writerow([
        "Desde",
        date_from or "Inicio",
        "Hasta",
        date_to or "Actual",
    ])

    writer.writerow([])

    writer.writerow([
        "Fecha",
        "Estado caja",
        "Total efectivo",
        "Total SINPE",
        "Total general",
        "Total tickets cobrados",
        "Primer ticket cobrado",
        "Ultimo ticket cobrado",
    ])

    total_cash = Decimal("0.00")
    total_sinpe = Decimal("0.00")
    total_general = Decimal("0.00")
    total_tickets = 0

    for cash_day in cash_days:
        summary = get_cash_day_summary(cash_day)

        first_ticket_number = ""
        last_ticket_number = ""

        if summary["first_payment"]:
            first_ticket_number = summary["first_payment"].ticket.ticket_number

        if summary["last_payment"]:
            last_ticket_number = summary["last_payment"].ticket.ticket_number

        writer.writerow([
            cash_day.business_date,
            cash_day.get_status_display(),
            summary["cash_total"],
            summary["sinpe_total"],
            summary["total_general"],
            summary["tickets_count"],
            first_ticket_number,
            last_ticket_number,
        ])

        total_cash += summary["cash_total"]
        total_sinpe += summary["sinpe_total"]
        total_general += summary["total_general"]
        total_tickets += summary["tickets_count"]

    writer.writerow([])
    writer.writerow([
        "TOTALES",
        "",
        total_cash,
        total_sinpe,
        total_general,
        total_tickets,
        "",
        "",
    ])

    return response