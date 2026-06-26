from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from cash.models import CashDay
from payments.models import Payment
from tickets.models import Ticket


@login_required
def cash_day_detail(request):
    today = timezone.localdate()

    cash_day, created = CashDay.objects.get_or_create(
        business_date=today,
        defaults={
            "status": CashDay.OPEN,
        },
    )

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

    first_ticket = tickets_today.order_by("created_at").first()
    last_ticket = tickets_today.order_by("-created_at").first()

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
            "first_ticket": first_ticket,
            "last_ticket": last_ticket,
        },
    )