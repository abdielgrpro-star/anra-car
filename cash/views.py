from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.permissions import user_can_authorize_sensitive_actions
from cash.models import CashDay
from cash.services import close_cash_day_manually, get_today_cash_day_for_view
from payments.models import Payment
from tickets.models import Ticket

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