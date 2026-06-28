from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.db import models, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse

from audit.models import AuditLog, OtpUsage
from accounts.permissions import user_can_authorize_sensitive_actions
from audit.models import AuditLog
from audit.utils import validate_sensitive_action_authorization
from cash.services import get_or_create_today_cash_day_for_operation
from catalog.models import Service
from payments.models import Payment
from accounts.models import Employee
from tickets.forms import (
    ApplyDiscountForm,
    CancelTicketForm,
    ChargeParkingTicketForm,
    ChargeWashTicketForm,
    ChargeWithoutCodeForm,
    EditParkingTicketForm,
    EditWashTicketForm,
    ParkingTicketForm,
    ReprintTicketForm,
    WashTicketForm,
)
from tickets.models import Customer, Ticket, TicketExtra
from tickets.utils import (
    calculate_parking_total,
    calculate_tax_from_total,
    generate_closing_code,
    generate_ticket_number,
)



def get_next_url(request, default_url_name="tickets:all_tickets"):
    next_url = request.GET.get("next") or request.POST.get("next")

    if next_url:
        return next_url

    return reverse(default_url_name)

@login_required
def home(request):
    return render(request, "home.html")

#Se crea el ticket de lavado
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

            cash_day = get_or_create_today_cash_day_for_operation()

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
                closing_code_for_print=closing_code,

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

#Se crea el ticket de parking
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

            cash_day = get_or_create_today_cash_day_for_operation()

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
                closing_code_for_print=closing_code,

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

#se ven detalles de ticket de parking
@login_required
def parking_ticket_detail(request, ticket_id):
    next_url = get_next_url(request)

    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
            "updated_by_employee",
        ),
        id=ticket_id,
    )

    return render(
        request,
        "tickets/parking_ticket_detail.html",
        {
            "ticket": ticket,
            "next_url": next_url,
        },
    )

#detalles del ticket de lavado
@login_required
def wash_ticket_detail(request, ticket_id):
    next_url = get_next_url(request)

    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
            "updated_by_employee",
        ).prefetch_related("ticket_extras"),
        id=ticket_id,
    )

    return render(
        request,
        "tickets/wash_ticket_detail.html",
        {
            "ticket": ticket,
            "next_url": next_url,
        },
    )

# Cobro de lavado con código de cierre
@login_required
@transaction.atomic
def charge_wash_ticket(request, ticket_id):
    next_url = get_next_url(request)

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
                        "next_url": next_url,
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
                        "next_url": next_url,
                    },
                )

            old_values = {
                "status": ticket.status,
                "paid_at": str(ticket.paid_at),
                "ticket_cash_day": str(ticket.cash_day.business_date),
                "payment": None,
            }

            payment_cash_day = get_or_create_today_cash_day_for_operation()

            Payment.objects.create(
                ticket=ticket,
                cash_day=payment_cash_day,
                received_by_employee=request.user,
                payment_method=payment_method,
                amount=ticket.total_with_tax,
                sinpe_reference=sinpe_reference,
            )
            
            ticket.cash_day = payment_cash_day
            ticket.status = Ticket.PAID
            ticket.paid_at = timezone.now()
            ticket.updated_by_employee = request.user

            ticket.save(
                update_fields=[
                    "cash_day",
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
                    "ticket_cash_day": str(ticket.cash_day.business_date),
                    "payment": {
                        "method": payment_method,
                        "amount": str(ticket.total_with_tax),
                        "sinpe_reference": sinpe_reference,
                        "cash_day": str(payment_cash_day.business_date),
                    },
                },
                reason="Ticket de lavado cobrado",
            )

            messages.success(
                request,
                f"Ticket {ticket.ticket_number} cobrado correctamente.",
            )

            return redirect(next_url)

    else:
        form = ChargeWashTicketForm()

    return render(
        request,
        "tickets/charge_wash_ticket.html",
        {
            "ticket": ticket,
            "form": form,
            "next_url": next_url,
        },
    )

#Cobro de parking con Codigo de cierre
@login_required
@transaction.atomic
def charge_parking_ticket(request, ticket_id):
    next_url = get_next_url(request)
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

    parking_total_before_discount = calculate_parking_total(
        minutes=parking_minutes,
        first_hour_price=ticket.parking_first_hour_price_snapshot,
        block_price=ticket.parking_block_price_snapshot,
        block_minutes=ticket.parking_block_minutes_snapshot,
    )

    parking_total = parking_total_before_discount - ticket.discount_amount

    if parking_total < Decimal("0.00"):
        parking_total = Decimal("0.00")

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
                        "next_url": next_url,
                    },
                )

            old_values = {
                "ticket_cash_day": str(ticket.cash_day.business_date),
                "status": ticket.status,
                "parking_exit_at": str(ticket.parking_exit_at),
                "parking_minutes": ticket.parking_minutes,
                "total_with_tax": str(ticket.total_with_tax),
                "payment": None,
            }

            payment_cash_day = get_or_create_today_cash_day_for_operation()

            Payment.objects.create(
                ticket=ticket,
                cash_day=payment_cash_day,
                received_by_employee=request.user,
                payment_method=payment_method,
                amount=parking_total,
                sinpe_reference=sinpe_reference,
            )

            ticket.cash_day = payment_cash_day
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
                    "cash_day",
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
                    "ticket_cash_day": str(ticket.cash_day.business_date),
                    "parking_entry_at": str(ticket.parking_entry_at),
                    "parking_exit_at": str(ticket.parking_exit_at),
                    "parking_minutes": ticket.parking_minutes,
                    "payment": {
                        "method": payment_method,
                        "amount": str(parking_total),
                        "sinpe_reference": sinpe_reference,
                        "cash_day": str(payment_cash_day.business_date),
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

            return redirect(next_url)

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
            "next_url": next_url,
        },
    )

#cobro de lavado sin codigo de cierre
@login_required
@transaction.atomic
def charge_wash_without_code(request, ticket_id):
    next_url = get_next_url(request)
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
        form = ChargeWithoutCodeForm(
            request.POST,
            request_user=request.user,
        )

        if form.is_valid():
            reason = form.cleaned_data["reason"]

            authorized_by_employee = form.cleaned_data.get(
                "authorized_by_employee"
            )
            otp_code = form.cleaned_data.get("otp_code")

            payment_method = form.cleaned_data["payment_method"]
            sinpe_reference = form.cleaned_data["sinpe_reference"].strip()

            is_authorized, otp_usage, final_authorizer = validate_sensitive_action_authorization(
                used_by_employee=request.user,
                authorized_by_employee=authorized_by_employee,
                ticket=ticket,
                action_type=OtpUsage.CLOSE_WITHOUT_CODE,
                otp_code=otp_code,
                reason=reason,
            )

            if not is_authorized:
                messages.error(
                    request,
                    "El OTP ingresado no es correcto.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    otp_usage=otp_usage,
                    action_type=AuditLog.CLOSE_WITHOUT_CODE,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "status": ticket.status,
                    },
                    new_values={
                        "attempt": "invalid_authorization_for_wash_without_code",
                        "authorized_by_employee": (
                            authorized_by_employee.username
                            if authorized_by_employee
                            else None
                        ),
                    },
                    reason=reason,
                )

                return render(
                    request,
                    "tickets/charge_without_code.html",
                    {
                        "ticket": ticket,
                        "form": form,
                        "ticket_kind": "lavado",
                        "next_url": next_url,
                    },
                )

            old_values = {
                "status": ticket.status,
                "paid_at": str(ticket.paid_at),
                "ticket_cash_day": str(ticket.cash_day.business_date),
                "payment": None,
            }

            payment_cash_day = get_or_create_today_cash_day_for_operation()

            Payment.objects.create(
                ticket=ticket,
                cash_day=payment_cash_day,
                received_by_employee=request.user,
                payment_method=payment_method,
                amount=ticket.total_with_tax,
                sinpe_reference=sinpe_reference,
            )

            ticket.cash_day = payment_cash_day
            ticket.status = Ticket.PAID
            ticket.paid_at = timezone.now()
            ticket.updated_by_employee = request.user
            ticket.save(
                update_fields=[
                    "cash_day",
                    "status",
                    "paid_at",
                    "updated_by_employee",
                    "updated_at",
                ]
            )

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                otp_usage=otp_usage,
                action_type=AuditLog.CLOSE_WITHOUT_CODE,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=old_values,
                new_values={
                    "status": ticket.status,
                    "paid_at": str(ticket.paid_at),
                    "ticket_cash_day": str(ticket.cash_day.business_date),
                    "payment": {
                        "method": payment_method,
                        "amount": str(ticket.total_with_tax),
                        "sinpe_reference": sinpe_reference,
                        "cash_day": str(payment_cash_day.business_date),
                    },
                    "authorized_by_employee": (
                        final_authorizer.username
                        if final_authorizer
                        else None
                    ),
                    "used_otp": otp_usage is not None,
                },
                reason=reason,
            )

            messages.success(
                request,
                f"Ticket {ticket.ticket_number} cobrado sin código correctamente.",
            )

            return redirect(next_url)

    else:
        form = ChargeWithoutCodeForm(
            request_user=request.user,
        )

    return render(
        request,
        "tickets/charge_without_code.html",
        {
            "ticket": ticket,
            "form": form,
            "ticket_kind": "lavado",
            "next_url": next_url,
        },
    )

#cobro de parqueo sin Codigo de cierre
@login_required
@transaction.atomic
def charge_parking_without_code(request, ticket_id):
    next_url = get_next_url(request)
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

    if parking_minutes < 1:
        parking_minutes = 1

    parking_total_before_discount = calculate_parking_total(
        minutes=parking_minutes,
        first_hour_price=ticket.parking_first_hour_price_snapshot,
        block_price=ticket.parking_block_price_snapshot,
        block_minutes=ticket.parking_block_minutes_snapshot,
    )

    parking_total = parking_total_before_discount - ticket.discount_amount

    if parking_total < Decimal("0.00"):
        parking_total = Decimal("0.00")

    tax_data = calculate_tax_from_total(
        total_with_tax=parking_total,
        tax_rate=ticket.tax_rate,
    )

    if request.method == "POST":
        form = ChargeWithoutCodeForm(
            request.POST,
            request_user=request.user,
        )

        if form.is_valid():
            reason = form.cleaned_data["reason"]

            authorized_by_employee = form.cleaned_data.get(
                "authorized_by_employee"
            )
            otp_code = form.cleaned_data.get("otp_code")

            payment_method = form.cleaned_data["payment_method"]
            sinpe_reference = form.cleaned_data["sinpe_reference"].strip()

            is_authorized, otp_usage, final_authorizer = validate_sensitive_action_authorization(
                used_by_employee=request.user,
                authorized_by_employee=authorized_by_employee,
                ticket=ticket,
                action_type=OtpUsage.CLOSE_WITHOUT_CODE,
                otp_code=otp_code,
                reason=reason,
            )

            if not is_authorized:
                messages.error(
                    request,
                    "El OTP ingresado no es correcto.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    otp_usage=otp_usage,
                    action_type=AuditLog.CLOSE_WITHOUT_CODE,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "status": ticket.status,
                    },
                    new_values={
                        "attempt": "invalid_authorization_for_parking_without_code",
                        "authorized_by_employee": (
                            authorized_by_employee.username
                            if authorized_by_employee
                            else None
                        ),
                    },
                    reason=reason,
                )

                return render(
                    request,
                    "tickets/charge_without_code.html",
                    {
                        "ticket": ticket,
                        "form": form,
                        "ticket_kind": "parqueo",
                        "exit_at": exit_at,
                        "parking_minutes": parking_minutes,
                        "parking_total": parking_total,
                        "tax_data": tax_data,
                        "next_url": next_url,
                    },
                )

            old_values = {
                "status": ticket.status,
                "parking_exit_at": str(ticket.parking_exit_at),
                "parking_minutes": ticket.parking_minutes,
                "subtotal_without_tax": str(ticket.subtotal_without_tax),
                "tax_amount": str(ticket.tax_amount),
                "total_with_tax": str(ticket.total_with_tax),
                "ticket_cash_day": str(ticket.cash_day.business_date),
                "payment": None,
            }

            payment_cash_day = get_or_create_today_cash_day_for_operation()

            Payment.objects.create(
                ticket=ticket,
                cash_day=payment_cash_day,
                received_by_employee=request.user,
                payment_method=payment_method,
                amount=parking_total,
                sinpe_reference=sinpe_reference,
            )

            ticket.cash_day = payment_cash_day
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
                    "cash_day",
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
                otp_usage=otp_usage,
                action_type=AuditLog.CLOSE_WITHOUT_CODE,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=old_values,
                new_values={
                    "status": ticket.status,
                    "ticket_cash_day": str(ticket.cash_day.business_date),
                    "parking_entry_at": str(ticket.parking_entry_at),
                    "parking_exit_at": str(ticket.parking_exit_at),
                    "parking_minutes": ticket.parking_minutes,
                    "payment": {
                        "method": payment_method,
                        "amount": str(parking_total),
                        "sinpe_reference": sinpe_reference,
                        "cash_day": str(payment_cash_day.business_date),
                    },
                    "subtotal_without_tax": str(ticket.subtotal_without_tax),
                    "tax_amount": str(ticket.tax_amount),
                    "total_with_tax": str(ticket.total_with_tax),
                    "authorized_by_employee": (
                        final_authorizer.username
                        if final_authorizer
                        else None
                    ),
                    "used_otp": otp_usage is not None,
                },
                reason=reason,
            )

            messages.success(
                request,
                f"Ticket de parqueo {ticket.ticket_number} cobrado sin código correctamente.",
            )

            return redirect(next_url)

    else:
        form = ChargeWithoutCodeForm(
            request_user=request.user,
        )

    return render(
        request,
        "tickets/charge_without_code.html",
        {
            "ticket": ticket,
            "form": form,
            "ticket_kind": "parqueo",
            "exit_at": exit_at,
            "parking_minutes": parking_minutes,
            "parking_total": parking_total,
            "tax_data": tax_data,
            "next_url": next_url,
        },
    )

# para ver todos los tickets
@login_required
def all_tickets(request):
    date = request.GET.get("date", "").strip()
    ticket_type = request.GET.get("ticket_type", "").strip()
    status = request.GET.get("status", "").strip()
    employee_id = request.GET.get("employee", "").strip()
    time_from = request.GET.get("time_from", "").strip()
    time_to = request.GET.get("time_to", "").strip()
    search = request.GET.get("search", "").strip()

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

    if date:
        tickets = tickets.filter(
            cash_day__business_date=date,
        )

    if ticket_type:
        tickets = tickets.filter(
            ticket_type=ticket_type,
        )

    if status:
        tickets = tickets.filter(
            status=status,
        )

    if employee_id:
        tickets = tickets.filter(
            created_by_employee_id=employee_id,
        )

    if time_from:
        tickets = tickets.filter(
            created_at__time__gte=time_from,
        )

    if time_to:
        tickets = tickets.filter(
            created_at__time__lte=time_to,
        )

    if search:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search)
            | Q(vehicle_plate__icontains=search)
            | Q(customer_name_snapshot__icontains=search)
            | Q(customer_phone_snapshot__icontains=search)
        )

    employees = Employee.objects.filter(
        is_active=True,
    ).order_by("username")

    return render(
        request,
        "tickets/all_tickets.html",
        {
            "tickets": tickets[:100],
            "date": date,
            "ticket_type": ticket_type,
            "status": status,
            "employee_id": employee_id,
            "time_from": time_from,
            "time_to": time_to,
            "search": search,
            "employees": employees,
            "ticket_type_choices": Ticket.TICKET_TYPE_CHOICES,
            "status_choices": Ticket.STATUS_CHOICES,
            "result_limit": 100,
        },
    )

#se cancelan tickets
@login_required
@transaction.atomic
def cancel_ticket(request, ticket_id):
    next_url = get_next_url(request)
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
        ),
        id=ticket_id,
    )

    if ticket.status not in [Ticket.PENDING_PAYMENT, Ticket.ACTIVE]:
        messages.error(
            request,
            "Solo se pueden anular tickets pendientes o parqueos activos.",
        )
        return redirect("tickets:all_tickets")

    if request.method == "POST":
        form = CancelTicketForm(
            request.POST,
            request_user=request.user,
        )

        if form.is_valid():
            reason = form.cleaned_data["reason"]

            authorized_by_employee = form.cleaned_data.get(
                "authorized_by_employee"
            )

            otp_code = form.cleaned_data.get("otp_code")

            is_authorized, otp_usage, final_authorizer = validate_sensitive_action_authorization(
                used_by_employee=request.user,
                authorized_by_employee=authorized_by_employee,
                ticket=ticket,
                action_type=OtpUsage.CANCEL_TICKET,
                otp_code=otp_code,
                reason=reason,
            )

            if not is_authorized:
                messages.error(
                    request,
                    "El OTP ingresado no es correcto.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    otp_usage=otp_usage,
                    action_type=AuditLog.CANCEL_TICKET,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "status": ticket.status,
                    },
                    new_values={
                        "attempt": "invalid_authorization_for_cancel_ticket",
                        "authorized_by_employee": (
                            authorized_by_employee.username
                            if authorized_by_employee
                            else None
                        ),
                    },
                    reason=reason,
                )

                return render(
                    request,
                    "tickets/cancel_ticket.html",
                    {
                        "ticket": ticket,
                        "form": form,
                        "next_url": next_url,
                    },
                )

            old_values = {
                "status": ticket.status,
                "cancelled_at": str(ticket.cancelled_at),
                "updated_by_employee": (
                    ticket.updated_by_employee.username
                    if ticket.updated_by_employee
                    else None
                ),
            }

            ticket.status = Ticket.CANCELLED
            ticket.cancelled_at = timezone.now()
            ticket.updated_by_employee = request.user
            ticket.save(
                update_fields=[
                    "status",
                    "cancelled_at",
                    "updated_by_employee",
                    "updated_at",
                ]
            )

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                otp_usage=otp_usage,
                action_type=AuditLog.CANCEL_TICKET,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=old_values,
                new_values={
                    "status": ticket.status,
                    "cancelled_at": str(ticket.cancelled_at),
                    "updated_by_employee": request.user.username,
                    "authorized_by_employee": (
                        final_authorizer.username
                        if final_authorizer
                        else None
                    ),
                    "used_otp": otp_usage is not None,
                },
                reason=reason,
            )

            messages.success(
                request,
                f"Ticket {ticket.ticket_number} anulado correctamente.",
            )

            if ticket.ticket_type == Ticket.WASH:
                return redirect(next_url)

            if ticket.ticket_type == Ticket.PARKING:
                return redirect(next_url)

            return redirect(next_url)

    else:
        form = CancelTicketForm(
            request_user=request.user,
        )

    return render(
        request,
        "tickets/cancel_ticket.html",
        {
            "ticket": ticket,
            "form": form,
            "next_url": next_url,
        },
    )

#se imprime por primera vez
@login_required
@transaction.atomic
def print_ticket(request, ticket_id):
    next_url = get_next_url(request)
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
            "last_printed_by_employee",
        ).prefetch_related("ticket_extras"),
        id=ticket_id,
    )

    old_values = {
        "print_count": ticket.print_count,
        "last_printed_at": str(ticket.last_printed_at),
        "last_printed_by_employee": (
            ticket.last_printed_by_employee.username
            if ticket.last_printed_by_employee
            else None
        ),
    }

    ticket.print_count += 1
    ticket.last_printed_at = timezone.now()
    ticket.last_printed_by_employee = request.user
    ticket.updated_by_employee = request.user

    ticket.save(
        update_fields=[
            "print_count",
            "last_printed_at",
            "last_printed_by_employee",
            "updated_by_employee",
            "updated_at",
        ]
    )

    AuditLog.objects.create(
        employee=request.user,
        ticket=ticket,
        action_type=AuditLog.REPRINT_TICKET if ticket.print_count > 1 else AuditLog.REPRINT_TICKET,
        entity_type="Ticket",
        entity_id=ticket.id,
        old_values=old_values,
        new_values={
            "print_count": ticket.print_count,
            "last_printed_at": str(ticket.last_printed_at),
            "last_printed_by_employee": request.user.username,
            "print_type": "first_print" if ticket.print_count == 1 else "reprint",
        },
        reason="Primera impresión" if ticket.print_count == 1 else "Reimpresión autorizada",
    )

    return render(
        request,
        "tickets/print_ticket.html",
        {
            "ticket": ticket,
            "next_url": next_url,
        },
    )

# reimprimir tickets despues de 1ra vez
@login_required
@transaction.atomic
def reprint_ticket(request, ticket_id):
    next_url = get_next_url(request)
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
            "last_printed_by_employee",
        ).prefetch_related("ticket_extras"),
        id=ticket_id,
    )

    # Si nunca se ha impreso, la primera impresión no requiere OTP.
    if ticket.print_count == 0:
        return redirect("tickets:print_ticket", ticket_id=ticket.id)

    if request.method == "POST":
        form = ReprintTicketForm(
            request.POST,
            request_user=request.user,
        )

        if form.is_valid():
            reason = form.cleaned_data["reason"]

            authorized_by_employee = form.cleaned_data.get(
                "authorized_by_employee"
            )
            otp_code = form.cleaned_data.get("otp_code")

            is_authorized, otp_usage, final_authorizer = validate_sensitive_action_authorization(
                used_by_employee=request.user,
                authorized_by_employee=authorized_by_employee,
                ticket=ticket,
                action_type=OtpUsage.REPRINT_TICKET,
                otp_code=otp_code,
                reason=reason,
            )

            if not is_authorized:
                messages.error(
                    request,
                    "El OTP ingresado no es correcto.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    otp_usage=otp_usage,
                    action_type=AuditLog.REPRINT_TICKET,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "print_count": ticket.print_count,
                        "last_printed_at": str(ticket.last_printed_at),
                        "last_printed_by_employee": (
                            ticket.last_printed_by_employee.username
                            if ticket.last_printed_by_employee
                            else None
                        ),
                    },
                    new_values={
                        "attempt": "invalid_authorization_for_reprint",
                        "authorized_by_employee": (
                            authorized_by_employee.username
                            if authorized_by_employee
                            else None
                        ),
                    },
                    reason=reason,
                )

                return render(
                    request,
                    "tickets/reprint_ticket.html",
                    {
                        "ticket": ticket,
                        "form": form,
                        "next_url": next_url,
                    },
                )

            old_values = {
                "print_count": ticket.print_count,
                "last_printed_at": str(ticket.last_printed_at),
                "last_printed_by_employee": (
                    ticket.last_printed_by_employee.username
                    if ticket.last_printed_by_employee
                    else None
                ),
            }

            ticket.print_count += 1
            ticket.last_printed_at = timezone.now()
            ticket.last_printed_by_employee = request.user
            ticket.updated_by_employee = request.user

            ticket.save(
                update_fields=[
                    "print_count",
                    "last_printed_at",
                    "last_printed_by_employee",
                    "updated_by_employee",
                    "updated_at",
                ]
            )

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                otp_usage=otp_usage,
                action_type=AuditLog.REPRINT_TICKET,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=old_values,
                new_values={
                    "print_count": ticket.print_count,
                    "last_printed_at": str(ticket.last_printed_at),
                    "last_printed_by_employee": request.user.username,
                    "authorized_by_employee": (
                        final_authorizer.username
                        if final_authorizer
                        else None
                    ),
                    "used_otp": otp_usage is not None,
                },
                reason=reason,
            )

            messages.success(
                request,
                f"Reimpresión del ticket {ticket.ticket_number} autorizada.",
            )

            return render(
                request,
                "tickets/print_ticket.html",
                {
                    "ticket": ticket,
                    "next_url": next_url,
                },
            )

    else:
        form = ReprintTicketForm(
            request_user=request.user,
        )

    return render(
        request,
        "tickets/reprint_ticket.html",
        {
            "ticket": ticket,
            "form": form,
            "next_url": next_url,
        },
    )

#editar tickets de lavado
@login_required
@transaction.atomic
def edit_wash_ticket(request, ticket_id):
    next_url = get_next_url(request)
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

    if ticket.status != Ticket.PENDING_PAYMENT:
        messages.error(
            request,
            "Solo se pueden editar lavados pendientes de pago.",
        )
        return redirect("tickets:wash_ticket_detail", ticket_id=ticket.id)

    if request.method == "POST":
        form = EditWashTicketForm(
            request.POST,
            ticket=ticket,
            request_user=request.user,
        )

        if form.is_valid():
            reason = form.cleaned_data["reason"]

            authorized_by_employee = form.cleaned_data.get(
                "authorized_by_employee"
            )
            otp_code = form.cleaned_data.get("otp_code")

            is_authorized, otp_usage, final_authorizer = validate_sensitive_action_authorization(
                used_by_employee=request.user,
                authorized_by_employee=authorized_by_employee,
                ticket=ticket,
                action_type=OtpUsage.EDIT_TICKET,
                otp_code=otp_code,
                reason=reason,
            )

            if not is_authorized:
                messages.error(
                    request,
                    "El OTP ingresado no es correcto.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    otp_usage=otp_usage,
                    action_type=AuditLog.EDIT_TICKET,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "status": ticket.status,
                    },
                    new_values={
                        "attempt": "invalid_authorization_for_edit_wash_ticket",
                        "authorized_by_employee": (
                            authorized_by_employee.username
                            if authorized_by_employee
                            else None
                        ),
                    },
                    reason=reason,
                )

                return render(
                    request,
                    "tickets/edit_wash_ticket.html",
                    {
                        "ticket": ticket,
                        "form": form,
                        "next_url": next_url,
                    },
                )

            old_ticket_extras = list(ticket.ticket_extras.all())

            old_values = {
                "customer_name": ticket.customer_name_snapshot,
                "customer_phone": ticket.customer_phone_snapshot,
                "vehicle_plate": ticket.vehicle_plate,
                "service": {
                    "id": ticket.service.id,
                    "name": ticket.service_name_snapshot,
                    "price_with_tax": str(ticket.service_price_with_tax_snapshot),
                },
                "extras": [
                    {
                        "id": ticket_extra.extra.id,
                        "name": ticket_extra.extra_name_snapshot,
                        "price_with_tax": str(ticket_extra.extra_price_with_tax_snapshot),
                    }
                    for ticket_extra in old_ticket_extras
                ],
                "subtotal_without_tax": str(ticket.subtotal_without_tax),
                "tax_amount": str(ticket.tax_amount),
                "discount_amount": str(ticket.discount_amount),
                "total_with_tax": str(ticket.total_with_tax),
            }

            customer_name = form.cleaned_data["customer_name"]
            customer_phone = form.cleaned_data["customer_phone"]
            vehicle_plate = form.cleaned_data["vehicle_plate"].upper().strip()
            service = form.cleaned_data["service"]
            extras = form.cleaned_data["extras"]

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

            if ticket.customer:
                ticket.customer.full_name = customer_name
                ticket.customer.phone = customer_phone
                ticket.customer.save(
                    update_fields=[
                        "full_name",
                        "phone",
                        "updated_at",
                    ]
                )

            ticket.customer_name_snapshot = customer_name
            ticket.customer_phone_snapshot = customer_phone
            ticket.vehicle_plate = vehicle_plate

            ticket.service = service
            ticket.service_name_snapshot = service.name
            ticket.service_price_with_tax_snapshot = service.price_with_tax

            ticket.subtotal_without_tax = tax_data["subtotal_without_tax"]
            ticket.tax_rate = service.tax_rate
            ticket.tax_amount = tax_data["tax_amount"]
            ticket.total_with_tax = tax_data["total_with_tax"]

            ticket.updated_by_employee = request.user

            ticket.save(
                update_fields=[
                    "customer_name_snapshot",
                    "customer_phone_snapshot",
                    "vehicle_plate",
                    "service",
                    "service_name_snapshot",
                    "service_price_with_tax_snapshot",
                    "subtotal_without_tax",
                    "tax_rate",
                    "tax_amount",
                    "total_with_tax",
                    "updated_by_employee",
                    "updated_at",
                ]
            )

            ticket.ticket_extras.all().delete()

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

            new_values = {
                "customer_name": ticket.customer_name_snapshot,
                "customer_phone": ticket.customer_phone_snapshot,
                "vehicle_plate": ticket.vehicle_plate,
                "service": {
                    "id": ticket.service.id,
                    "name": ticket.service_name_snapshot,
                    "price_with_tax": str(ticket.service_price_with_tax_snapshot),
                },
                "extras": [
                    {
                        "id": ticket_extra.extra.id,
                        "name": ticket_extra.extra_name_snapshot,
                        "price_with_tax": str(ticket_extra.extra_price_with_tax_snapshot),
                    }
                    for ticket_extra in ticket.ticket_extras.all()
                ],
                "subtotal_without_tax": str(ticket.subtotal_without_tax),
                "tax_amount": str(ticket.tax_amount),
                "discount_amount": str(ticket.discount_amount),
                "total_with_tax": str(ticket.total_with_tax),
                "authorized_by_employee": (
                    final_authorizer.username
                    if final_authorizer
                    else None
                ),
                "used_otp": otp_usage is not None,
            }

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                otp_usage=otp_usage,
                action_type=AuditLog.EDIT_TICKET,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=old_values,
                new_values=new_values,
                reason=reason,
            )

            messages.success(
                request,
                f"Ticket {ticket.ticket_number} editado correctamente.",
            )

            return redirect(next_url)

    else:
        form = EditWashTicketForm(
            ticket=ticket,
            request_user=request.user,
        )

    return render(
        request,
        "tickets/edit_wash_ticket.html",
        {
            "ticket": ticket,
            "form": form,
            "next_url": next_url,
        },
    )

#editar tickets de parking
@login_required
@transaction.atomic
def edit_parking_ticket(request, ticket_id):
    next_url = get_next_url(request)
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

    if ticket.status != Ticket.ACTIVE:
        messages.error(
            request,
            "Solo se pueden editar parqueos activos.",
        )
        return redirect("tickets:parking_ticket_detail", ticket_id=ticket.id)

    if request.method == "POST":
        form = EditParkingTicketForm(
            request.POST,
            ticket=ticket,
            request_user=request.user,
        )

        if form.is_valid():
            reason = form.cleaned_data["reason"]

            authorized_by_employee = form.cleaned_data.get(
                "authorized_by_employee"
            )
            otp_code = form.cleaned_data.get("otp_code")

            is_authorized, otp_usage, final_authorizer = validate_sensitive_action_authorization(
                used_by_employee=request.user,
                authorized_by_employee=authorized_by_employee,
                ticket=ticket,
                action_type=OtpUsage.EDIT_TICKET,
                otp_code=otp_code,
                reason=reason,
            )

            if not is_authorized:
                messages.error(
                    request,
                    "El OTP ingresado no es correcto.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    otp_usage=otp_usage,
                    action_type=AuditLog.EDIT_TICKET,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "status": ticket.status,
                        "parking_entry_at": str(ticket.parking_entry_at),
                    },
                    new_values={
                        "attempt": "invalid_authorization_for_edit_parking_ticket",
                        "authorized_by_employee": (
                            authorized_by_employee.username
                            if authorized_by_employee
                            else None
                        ),
                    },
                    reason=reason,
                )

                return render(
                    request,
                    "tickets/edit_parking_ticket.html",
                    {
                        "ticket": ticket,
                        "form": form,
                        "next_url": next_url,
                    },
                )

            old_values = {
                "customer_name": ticket.customer_name_snapshot,
                "customer_phone": ticket.customer_phone_snapshot,
                "vehicle_plate": ticket.vehicle_plate,
                "parking_entry_at": str(ticket.parking_entry_at),
                "status": ticket.status,
                "total_with_tax": str(ticket.total_with_tax),
            }

            customer_name = form.cleaned_data["customer_name"]
            customer_phone = form.cleaned_data["customer_phone"]
            vehicle_plate = form.cleaned_data["vehicle_plate"].upper().strip()

            if ticket.customer:
                ticket.customer.full_name = customer_name
                ticket.customer.phone = customer_phone
                ticket.customer.save(
                    update_fields=[
                        "full_name",
                        "phone",
                        "updated_at",
                    ]
                )

            ticket.customer_name_snapshot = customer_name
            ticket.customer_phone_snapshot = customer_phone
            ticket.vehicle_plate = vehicle_plate
            ticket.updated_by_employee = request.user

            ticket.save(
                update_fields=[
                    "customer_name_snapshot",
                    "customer_phone_snapshot",
                    "vehicle_plate",
                    "updated_by_employee",
                    "updated_at",
                ]
            )

            new_values = {
                "customer_name": ticket.customer_name_snapshot,
                "customer_phone": ticket.customer_phone_snapshot,
                "vehicle_plate": ticket.vehicle_plate,
                "parking_entry_at": str(ticket.parking_entry_at),
                "status": ticket.status,
                "total_with_tax": str(ticket.total_with_tax),
                "authorized_by_employee": (
                    final_authorizer.username
                    if final_authorizer
                    else None
                ),
                "used_otp": otp_usage is not None,
            }

            AuditLog.objects.create(
                employee=request.user,
                ticket=ticket,
                otp_usage=otp_usage,
                action_type=AuditLog.EDIT_TICKET,
                entity_type="Ticket",
                entity_id=ticket.id,
                old_values=old_values,
                new_values=new_values,
                reason=reason,
            )

            messages.success(
                request,
                f"Ticket de parqueo {ticket.ticket_number} editado correctamente.",
            )

            return redirect(next_url)

    else:
        form = EditParkingTicketForm(
            ticket=ticket,
            request_user=request.user,
        )

    return render(
        request,
        "tickets/edit_parking_ticket.html",
        {
            "ticket": ticket,
            "form": form,
            "next_url": next_url,
        },
    )

#se aplica descuento
@login_required
@transaction.atomic
def apply_discount(request, ticket_id):
    next_url = get_next_url(request)


    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "customer",
            "service",
            "cash_day",
            "created_by_employee",
        ).prefetch_related("ticket_extras"),
        id=ticket_id,
    )

    if ticket.status not in [Ticket.PENDING_PAYMENT, Ticket.ACTIVE]:
        messages.error(
            request,
            "Solo se pueden aplicar descuentos a tickets pendientes o parqueos activos.",
        )

        if ticket.ticket_type == Ticket.WASH:
            return redirect(next_url)

        return redirect(next_url)

    if request.method == "POST":
        form = ApplyDiscountForm(
            request.POST,
            ticket=ticket,
            request_user=request.user,
        )

        if form.is_valid():
            reason = form.cleaned_data["reason"]

            authorized_by_employee = form.cleaned_data.get(
                "authorized_by_employee"
            )
            otp_code = form.cleaned_data.get("otp_code")

            discount_amount = form.cleaned_data["discount_amount"]
            remove_discount = form.cleaned_data.get("remove_discount", False)

            if remove_discount:
                discount_amount = Decimal("0.00")

            is_authorized, otp_usage, final_authorizer = validate_sensitive_action_authorization(
                used_by_employee=request.user,
                authorized_by_employee=authorized_by_employee,
                ticket=ticket,
                action_type=OtpUsage.APPLY_DISCOUNT,
                otp_code=otp_code,
                reason=reason,
            )

            if not is_authorized:
                messages.error(
                    request,
                    "El OTP ingresado no es correcto. Verifique el código con el administrador e inténtelo nuevamente.",
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    otp_usage=otp_usage,
                    action_type=AuditLog.APPLY_DISCOUNT,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values={
                        "discount_amount": str(ticket.discount_amount),
                        "total_with_tax": str(ticket.total_with_tax),
                    },
                    new_values={
                        "attempt": "invalid_authorization_for_apply_discount",
                        "authorized_by_employee": (
                            authorized_by_employee.username
                            if authorized_by_employee
                            else None
                        ),
                    },
                    reason=reason,
                )

                return render(
                    request,
                    "tickets/apply_discount.html",
                    {
                        "ticket": ticket,
                        "form": form,
                        "next_url": next_url,
                    },
                )

            old_values = {
                "discount_amount": str(ticket.discount_amount),
                "subtotal_without_tax": str(ticket.subtotal_without_tax),
                "tax_amount": str(ticket.tax_amount),
                "total_with_tax": str(ticket.total_with_tax),
            }

            if ticket.ticket_type == Ticket.WASH:
                gross_total = ticket.service_price_with_tax_snapshot

                for ticket_extra in ticket.ticket_extras.all():
                    gross_total += ticket_extra.extra_price_with_tax_snapshot

                if discount_amount > gross_total:
                    form.add_error(
                        "discount_amount",
                        "El descuento no puede ser mayor al total del ticket.",
                    )

                    return render(
                        request,
                        "tickets/apply_discount.html",
                        {
                            "ticket": ticket,
                            "form": form,
                            "next_url": next_url,
                        },
                    )

                new_total = gross_total - discount_amount

                tax_data = calculate_tax_from_total(
                    total_with_tax=new_total,
                    tax_rate=ticket.tax_rate,
                )

                ticket.discount_amount = discount_amount
                ticket.subtotal_without_tax = tax_data["subtotal_without_tax"]
                ticket.tax_amount = tax_data["tax_amount"]
                ticket.total_with_tax = tax_data["total_with_tax"]
                ticket.updated_by_employee = request.user

                ticket.save(
                    update_fields=[
                        "discount_amount",
                        "subtotal_without_tax",
                        "tax_amount",
                        "total_with_tax",
                        "updated_by_employee",
                        "updated_at",
                    ]
                )

            else:
                if discount_amount > ticket.total_with_tax:
                    form.add_error(
                        "discount_amount",
                        "El descuento no puede ser mayor al monto actual del parqueo.",
                    )

                    return render(
                        request,
                        "tickets/apply_discount.html",
                        {
                            "ticket": ticket,
                            "form": form,
                            "next_url": next_url,
                        },
                    )

                ticket.discount_amount = discount_amount
                ticket.updated_by_employee = request.user

                ticket.save(
                    update_fields=[
                        "discount_amount",
                        "updated_by_employee",
                        "updated_at",
                    ]
                )

                AuditLog.objects.create(
                    employee=request.user,
                    ticket=ticket,
                    otp_usage=otp_usage,
                    action_type=AuditLog.APPLY_DISCOUNT,
                    entity_type="Ticket",
                    entity_id=ticket.id,
                    old_values=old_values,
                    new_values={
                        "discount_amount": str(ticket.discount_amount),
                        "subtotal_without_tax": str(ticket.subtotal_without_tax),
                        "tax_amount": str(ticket.tax_amount),
                        "total_with_tax": str(ticket.total_with_tax),
                        "remove_discount": remove_discount,
                        "authorized_by_employee": (
                            final_authorizer.username
                            if final_authorizer
                            else None
                        ),
                        "used_otp": otp_usage is not None,
                    },
                    reason=reason,
                )

            if discount_amount == Decimal("0.00"):
                messages.success(
                    request,
                    f"Descuento eliminado correctamente del ticket {ticket.ticket_number}.",
                )
            else:
                messages.success(
                    request,
                    f"Descuento actualizado correctamente en el ticket {ticket.ticket_number}.",
                )

            if ticket.ticket_type == Ticket.WASH:
                return redirect(next_url)

            return redirect(next_url)

    else:
        form = ApplyDiscountForm(
            ticket=ticket,
            request_user=request.user,
        )

    return render(
        request,
        "tickets/apply_discount.html",
        {
            "ticket": ticket,
            "form": form,
            "next_url": next_url,
        },
    )

@login_required
@transaction.atomic
def reopen_ticket(request, ticket_id):
    if not user_can_authorize_sensitive_actions(request.user):
        messages.error(
            request,
            "No tiene permisos para reabrir tickets.",
        )
        return redirect("home")

    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "cash_day",
            "payment",
        ),
        id=ticket_id,
    )

    next_url = get_next_url(request)

    if ticket.status != Ticket.PAID:
        messages.error(
            request,
            "Solo se pueden reabrir tickets que ya fueron pagados.",
        )
        return redirect(next_url)

    payment = getattr(ticket, "payment", None)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()

        if not reason:
            messages.error(
                request,
                "Debe indicar el motivo de la reapertura.",
            )
            return render(
                request,
                "tickets/reopen_ticket_confirm.html",
                {
                    "ticket": ticket,
                    "next_url": next_url,
                },
            )

        old_values = {
            "status": ticket.status,
            "paid_at": str(ticket.paid_at),
            "ticket_cash_day": (
                str(ticket.cash_day.business_date)
                if ticket.cash_day
                else None
            ),
            "payment": None,
        }

        if payment:
            old_values["payment"] = {
                "id": payment.id,
                "cash_day": str(payment.cash_day.business_date),
                "method": payment.payment_method,
                "amount": str(payment.amount),
                "sinpe_reference": payment.sinpe_reference,
                "received_by_employee": payment.received_by_employee.username,
                "created_at": str(payment.created_at),
            }

            payment.delete()

        if ticket.ticket_type == Ticket.WASH:
            new_status = Ticket.PENDING_PAYMENT
        else:
            new_status = Ticket.ACTIVE

        ticket.status = new_status
        ticket.paid_at = None
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
            action_type=AuditLog.REOPEN_TICKET,
            entity_type="Ticket",
            entity_id=str(ticket.id),
            old_values=old_values,
            new_values={
                "status": ticket.status,
                "paid_at": None,
                "payment": None,
                "message": "El ticket fue reabierto y el pago anterior fue removido de la caja.",
            },
            reason=reason,
        )

        messages.success(
            request,
            "Ticket reabierto correctamente. El pago anterior ya no cuenta en caja.",
        )

        return redirect(next_url)

    return render(
        request,
        "tickets/reopen_ticket_confirm.html",
        {
            "ticket": ticket,
            "next_url": next_url,
        },
    )