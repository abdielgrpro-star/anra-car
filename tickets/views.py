from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from audit.models import AuditLog
from cash.models import CashDay
from tickets.forms import WashTicketForm
from tickets.models import Customer, Ticket, TicketExtra
from tickets.utils import (
    calculate_tax_from_total,
    generate_closing_code,
    generate_ticket_number,
)


@login_required
def home(request):
    return render(request, "home.html")


@login_required
@transaction.atomic
def create_wash_ticket(request):
    if request.method == "POST":
        form = WashTicketForm(request.POST)

        if form.is_valid():
            customer_name = form.cleaned_data["customer_name"]
            customer_phone = form.cleaned_data["customer_phone"]
            vehicle_plate = form.cleaned_data["vehicle_plate"].upper().strip()
            service = form.cleaned_data["service"]
            extras = form.cleaned_data["extras"]

            customer = Customer.objects.create(
                full_name=customer_name,
                phone=customer_phone,
            )

            cash_day, created = CashDay.objects.get_or_create(
                business_date=timezone.localdate(),
                defaults={
                    "status": CashDay.OPEN,
                },
            )

            service_total = service.price_with_tax
            extras_total = sum(
                (extra.price_with_tax for extra in extras),
                Decimal("0.00"),
            )

            total_with_tax = service_total + extras_total
            tax_data = calculate_tax_from_total(
                total_with_tax=total_with_tax,
                tax_rate=service.tax_rate,
            )

            closing_code = generate_closing_code()
            ticket_number = generate_ticket_number(prefix="L")

            ticket = Ticket.objects.create(
                ticket_number=ticket_number,
                ticket_type=Ticket.WASH,
                status=Ticket.PENDING_PAYMENT,

                customer=customer,
                service=service,
                cash_day=cash_day,

                customer_name_snapshot=customer_name,
                customer_phone_snapshot=customer_phone,
                vehicle_plate=vehicle_plate,

                service_name_snapshot=service.name,
                service_price_with_tax_snapshot=service.price_with_tax,

                subtotal_without_tax=tax_data["subtotal_without_tax"],
                tax_rate=service.tax_rate,
                tax_amount=tax_data["tax_amount"],
                discount_amount=Decimal("0.00"),
                total_with_tax=tax_data["total_with_tax"],

                closing_code_hash=make_password(closing_code),

                created_by_employee=request.user,
            )

            for extra in extras:
                extra_tax_data = calculate_tax_from_total(
                    total_with_tax=extra.price_with_tax,
                    tax_rate=extra.tax_rate,
                )

                TicketExtra.objects.create(
                    ticket=ticket,
                    extra=extra,
                    extra_name_snapshot=extra.name,
                    extra_price_with_tax_snapshot=extra.price_with_tax,
                    tax_rate_snapshot=extra.tax_rate,
                    subtotal_without_tax=extra_tax_data["subtotal_without_tax"],
                    tax_amount=extra_tax_data["tax_amount"],
                    total_with_tax=extra_tax_data["total_with_tax"],
                )

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                action_type=AuditLog.CREATE_WASH_TICKET,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=None,
                new_values={
                    "ticket_number": ticket.ticket_number,
                    "ticket_type": ticket.ticket_type,
                    "status": ticket.status,
                    "customer_name": ticket.customer_name_snapshot,
                    "customer_phone": ticket.customer_phone_snapshot,
                    "vehicle_plate": ticket.vehicle_plate,
                    "service": {
                        "name": ticket.service_name_snapshot,
                        "price_with_tax": str(ticket.service_price_with_tax_snapshot),
                    },
                    "extras": [
                        {
                            "name": ticket_extra.extra_name_snapshot,
                            "price_with_tax": str(ticket_extra.extra_price_with_tax_snapshot),
                        }
                        for ticket_extra in ticket.ticket_extras.all()
                    ],
                    "total_with_tax": str(ticket.total_with_tax),
                },
                reason="Ticket de lavado creado",
            )

            request.session["last_closing_code"] = closing_code

            messages.success(
                request,
                f"Ticket {ticket.ticket_number} creado correctamente.",
            )

            return redirect("tickets:wash_ticket_detail", ticket_id=ticket.id)

    else:
        form = WashTicketForm()

    return render(
        request,
        "tickets/create_wash_ticket.html",
        {
            "form": form,
        },
    )


@login_required
def wash_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
        ).prefetch_related("ticket_extras"),
        id=ticket_id,
        ticket_type=Ticket.WASH,
    )

    closing_code = request.session.pop("last_closing_code", None)

    return render(
        request,
        "tickets/wash_ticket_detail.html",
        {
            "ticket": ticket,
            "closing_code": closing_code,
        },
    )

@login_required
def pending_wash_tickets(request):
    tickets = (
        Ticket.objects
        .select_related("customer", "service", "cash_day", "created_by_employee")
        .filter(
            ticket_type=Ticket.WASH,
            status=Ticket.PENDING_PAYMENT,
        )
        .order_by("-created_at")
    )

    search_query = request.GET.get("q", "").strip()

    if search_query:
        tickets = tickets.filter(
            models.Q(ticket_number__icontains=search_query)
            | models.Q(vehicle_plate__icontains=search_query)
            | models.Q(customer_name_snapshot__icontains=search_query)
            | models.Q(customer_phone_snapshot__icontains=search_query)
        )

    return render(
        request,
        "tickets/pending_wash_tickets.html",
        {
            "tickets": tickets,
            "search_query": search_query,
        },
    )