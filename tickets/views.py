from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from audit.models import AuditLog
from cash.models import CashDay
from catalog.models import Service
from payments.models import Payment
from tickets.forms import ChargeWashTicketForm, ChargeParkingTicketForm, ParkingTicketForm, WashTicketForm
from tickets.models import Customer, Ticket, TicketExtra
from tickets.utils import (
    calculate_parking_total,
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
@transaction.atomic
def create_parking_ticket(request):
    if request.method == "POST":
        form = ParkingTicketForm(request.POST)

        if form.is_valid():
            customer_name = form.cleaned_data["customer_name"]
            customer_phone = form.cleaned_data["customer_phone"]
            vehicle_plate = form.cleaned_data["vehicle_plate"].upper().strip()

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

            parking_service = get_object_or_404(
                Service,
                service_type=Service.PARKING,
                is_active=True,
            )

            first_hour_price = Decimal("1000.00")
            block_price = Decimal("500.00")
            block_minutes = 30

            tax_data = calculate_tax_from_total(
                total_with_tax=first_hour_price,
                tax_rate=parking_service.tax_rate,
            )

            closing_code = generate_closing_code()
            ticket_number = generate_ticket_number(prefix="P")

            ticket = Ticket.objects.create(
                ticket_number=ticket_number,
                ticket_type=Ticket.PARKING,
                status=Ticket.ACTIVE,

                customer=customer,
                service=parking_service,
                cash_day=cash_day,

                customer_name_snapshot=customer_name,
                customer_phone_snapshot=customer_phone,
                vehicle_plate=vehicle_plate,

                service_name_snapshot=parking_service.name,
                service_price_with_tax_snapshot=parking_service.price_with_tax,

                subtotal_without_tax=tax_data["subtotal_without_tax"],
                tax_rate=parking_service.tax_rate,
                tax_amount=tax_data["tax_amount"],
                discount_amount=Decimal("0.00"),
                total_with_tax=first_hour_price,

                closing_code_hash=make_password(closing_code),

                parking_entry_at=timezone.now(),
                parking_first_hour_price_snapshot=first_hour_price,
                parking_block_price_snapshot=block_price,
                parking_block_minutes_snapshot=block_minutes,

                created_by_employee=request.user,
            )

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                action_type=AuditLog.CREATE_PARKING_TICKET,
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
                    "parking_entry_at": str(ticket.parking_entry_at),
                    "parking_first_hour_price": str(ticket.parking_first_hour_price_snapshot),
                    "parking_block_price": str(ticket.parking_block_price_snapshot),
                    "parking_block_minutes": ticket.parking_block_minutes_snapshot,
                },
                reason="Ticket de parqueo creado",
            )

            request.session["last_closing_code"] = closing_code

            messages.success(
                request,
                f"Ticket de parqueo {ticket.ticket_number} creado correctamente.",
            )

            return redirect("tickets:parking_ticket_detail", ticket_id=ticket.id)

    else:
        form = ParkingTicketForm()

    return render(
        request,
        "tickets/create_parking_ticket.html",
        {
            "form": form,
        },
    )

@login_required
def parking_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
        ),
        id=ticket_id,
        ticket_type=Ticket.PARKING,
    )

    closing_code = request.session.pop("last_closing_code", None)

    return render(
        request,
        "tickets/parking_ticket_detail.html",
        {
            "ticket": ticket,
            "closing_code": closing_code,
        },
    )

@login_required
def active_parking_tickets(request):
    tickets = (
        Ticket.objects
        .select_related("customer", "service", "cash_day", "created_by_employee")
        .filter(
            ticket_type=Ticket.PARKING,
            status=Ticket.ACTIVE,
        )
        .order_by("-parking_entry_at")
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
        "tickets/active_parking_tickets.html",
        {
            "tickets": tickets,
            "search_query": search_query,
        },
    )

@login_required
@transaction.atomic
def charge_parking_ticket(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
        ),
        id=ticket_id,
        ticket_type=Ticket.PARKING,
        status=Ticket.ACTIVE,
    )

    exit_at = timezone.now()

    elapsed_seconds = (exit_at - ticket.parking_entry_at).total_seconds()
    parking_minutes = int(elapsed_seconds // 60)

    # Para evitar cobrar 0 minutos si apenas se creó el ticket
    if parking_minutes < 1:
        parking_minutes = 1

    parking_total = calculate_parking_total(
        minutes=parking_minutes,
        first_hour_price=ticket.parking_first_hour_price_snapshot,
        block_price=ticket.parking_block_price_snapshot,
        block_minutes=ticket.parking_block_minutes_snapshot,
    )

    tax_data = calculate_tax_from_total(
        total_with_tax=parking_total,
        tax_rate=ticket.tax_rate,
    )

    if request.method == "POST":
        form = ChargeParkingTicketForm(request.POST)

        if form.is_valid():
            closing_code = form.cleaned_data["closing_code"].upper().strip()
            payment_method = form.cleaned_data["payment_method"]
            sinpe_reference = form.cleaned_data["sinpe_reference"].strip()

            is_valid_code = check_password(
                closing_code,
                ticket.closing_code_hash,
            )

            if not is_valid_code:
                messages.error(
                    request,
                    "El código de cierre no es correcto.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    action_type=AuditLog.CLOSE_WITHOUT_CODE,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "status": ticket.status,
                    },
                    new_values={
                        "attempt": "invalid_parking_closing_code",
                    },
                    reason="Intento fallido de cobro de parqueo con código incorrecto",
                )

                return render(
                    request,
                    "tickets/charge_parking_ticket.html",
                    {
                        "ticket": ticket,
                        "form": form,
                        "exit_at": exit_at,
                        "parking_minutes": parking_minutes,
                        "parking_total": parking_total,
                        "tax_data": tax_data,
                    },
                )

            old_values = {
                "status": ticket.status,
                "parking_exit_at": str(ticket.parking_exit_at),
                "parking_minutes": ticket.parking_minutes,
                "total_with_tax": str(ticket.total_with_tax),
                "payment": None,
            }

            Payment.objects.create(
                ticket=ticket,
                cash_day=ticket.cash_day,
                received_by_employee=request.user,
                payment_method=payment_method,
                amount=parking_total,
                sinpe_reference=sinpe_reference,
            )

            ticket.status = Ticket.PAID
            ticket.parking_exit_at = exit_at
            ticket.parking_minutes = parking_minutes
            ticket.subtotal_without_tax = tax_data["subtotal_without_tax"]
            ticket.tax_amount = tax_data["tax_amount"]
            ticket.total_with_tax = tax_data["total_with_tax"]
            ticket.paid_at = exit_at
            ticket.updated_by_employee = request.user

            ticket.save(
                update_fields=[
                    "status",
                    "parking_exit_at",
                    "parking_minutes",
                    "subtotal_without_tax",
                    "tax_amount",
                    "total_with_tax",
                    "paid_at",
                    "updated_by_employee",
                    "updated_at",
                ]
            )

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                action_type=AuditLog.CHARGE_PARKING_TICKET,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=old_values,
                new_values={
                    "status": ticket.status,
                    "parking_entry_at": str(ticket.parking_entry_at),
                    "parking_exit_at": str(ticket.parking_exit_at),
                    "parking_minutes": ticket.parking_minutes,
                    "payment": {
                        "method": payment_method,
                        "amount": str(parking_total),
                        "sinpe_reference": sinpe_reference,
                    },
                    "subtotal_without_tax": str(ticket.subtotal_without_tax),
                    "tax_amount": str(ticket.tax_amount),
                    "total_with_tax": str(ticket.total_with_tax),
                },
                reason="Ticket de parqueo cobrado",
            )

            messages.success(
                request,
                f"Ticket de parqueo {ticket.ticket_number} cobrado correctamente.",
            )

            return redirect("tickets:parking_ticket_detail", ticket_id=ticket.id)

    else:
        form = ChargeParkingTicketForm()

    return render(
        request,
        "tickets/charge_parking_ticket.html",
        {
            "ticket": ticket,
            "form": form,
            "exit_at": exit_at,
            "parking_minutes": parking_minutes,
            "parking_total": parking_total,
            "tax_data": tax_data,
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

@login_required
@transaction.atomic
def charge_wash_ticket(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
        ).prefetch_related("ticket_extras"),
        id=ticket_id,
        ticket_type=Ticket.WASH,
        status=Ticket.PENDING_PAYMENT,
    )

    if request.method == "POST":
        form = ChargeWashTicketForm(request.POST)

        if form.is_valid():
            closing_code = form.cleaned_data["closing_code"].upper().strip()
            payment_method = form.cleaned_data["payment_method"]
            sinpe_reference = form.cleaned_data["sinpe_reference"].strip()

            is_valid_code = check_password(
                closing_code,
                ticket.closing_code_hash,
            )

            if not is_valid_code:
                messages.error(
                    request,
                    "El código de cierre no es correcto.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    action_type=AuditLog.CLOSE_WITHOUT_CODE,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "status": ticket.status,
                    },
                    new_values={
                        "attempt": "invalid_closing_code",
                    },
                    reason="Intento fallido de cobro con código incorrecto",
                )

                return render(
                    request,
                    "tickets/charge_wash_ticket.html",
                    {
                        "ticket": ticket,
                        "form": form,
                    },
                )

            if payment_method == Payment.SINPE and not sinpe_reference:
                form.add_error(
                    "sinpe_reference",
                    "La referencia SINPE es recomendable para este método de pago.",
                )

                return render(
                    request,
                    "tickets/charge_wash_ticket.html",
                    {
                        "ticket": ticket,
                        "form": form,
                    },
                )

            old_values = {
                "status": ticket.status,
                "paid_at": str(ticket.paid_at),
                "payment": None,
            }

            Payment.objects.create(
                ticket=ticket,
                cash_day=ticket.cash_day,
                received_by_employee=request.user,
                payment_method=payment_method,
                amount=ticket.total_with_tax,
                sinpe_reference=sinpe_reference,
            )

            ticket.status = Ticket.PAID
            ticket.paid_at = timezone.now()
            ticket.updated_by_employee = request.user
            ticket.save(
                update_fields=[
                    "status",
                    "paid_at",
                    "updated_by_employee",
                    "updated_at",
                ]
            )

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                action_type=AuditLog.CHARGE_WASH_TICKET,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=old_values,
                new_values={
                    "status": ticket.status,
                    "paid_at": str(ticket.paid_at),
                    "payment": {
                        "method": payment_method,
                        "amount": str(ticket.total_with_tax),
                        "sinpe_reference": sinpe_reference,
                    },
                },
                reason="Ticket de lavado cobrado",
            )

            messages.success(
                request,
                f"Ticket {ticket.ticket_number} cobrado correctamente.",
            )

            return redirect("tickets:wash_ticket_detail", ticket_id=ticket.id)

    else:
        form = ChargeWashTicketForm()

    return render(
        request,
        "tickets/charge_wash_ticket.html",
        {
            "ticket": ticket,
            "form": form,
        },
    )


@login_required
def all_tickets(request):
    tickets = (
        Ticket.objects
        .select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
            "updated_by_employee",
        )
        .order_by("-created_at")
    )

    search_query = request.GET.get("q", "").strip()
    date_query = request.GET.get("date", "").strip()
    ticket_type = request.GET.get("ticket_type", "").strip()
    status = request.GET.get("status", "").strip()

    if search_query:
        tickets = tickets.filter(
            models.Q(ticket_number__icontains=search_query)
            | models.Q(vehicle_plate__icontains=search_query)
            | models.Q(customer_name_snapshot__icontains=search_query)
            | models.Q(customer_phone_snapshot__icontains=search_query)
        )

    if date_query:
        tickets = tickets.filter(
            cash_day__business_date=date_query
        )

    if ticket_type:
        tickets = tickets.filter(
            ticket_type=ticket_type
        )

    if status:
        tickets = tickets.filter(
            status=status
        )

    return render(
        request,
        "tickets/all_tickets.html",
        {
            "tickets": tickets,
            "search_query": search_query,
            "date_query": date_query,
            "ticket_type": ticket_type,
            "status": status,
            "ticket_type_choices": Ticket.TICKET_TYPE_CHOICES,
            "status_choices": Ticket.STATUS_CHOICES,
        },
    )