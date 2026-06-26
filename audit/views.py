from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date

from accounts.models import Employee
from accounts.permissions import user_can_authorize_sensitive_actions
from audit.models import AuditLog


@login_required
def audit_log_list(request):
    if not user_can_authorize_sensitive_actions(request.user):
        messages.error(
            request,
            "No tiene permisos para ver auditoría.",
        )
        return redirect("home")

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    employee_id = request.GET.get("employee", "").strip()
    action_type = request.GET.get("action_type", "").strip()
    otp_status = request.GET.get("otp_status", "").strip()
    search = request.GET.get("search", "").strip()

    logs = (
        AuditLog.objects
        .select_related(
            "employee",
            "ticket",
            "otp_usage",
            "otp_usage__authorized_by_employee",
            "otp_usage__used_by_employee",
        )
        .order_by("-created_at")
    )

    if date_from:
        parsed_date_from = parse_date(date_from)

        if parsed_date_from:
            logs = logs.filter(created_at__date__gte=parsed_date_from)

    if date_to:
        parsed_date_to = parse_date(date_to)

        if parsed_date_to:
            logs = logs.filter(created_at__date__lte=parsed_date_to)

    if employee_id:
        logs = logs.filter(employee_id=employee_id)

    if action_type:
        logs = logs.filter(action_type=action_type)

    if otp_status == "used":
        logs = logs.filter(otp_usage__isnull=False)

    if otp_status == "not_used":
        logs = logs.filter(otp_usage__isnull=True)

    if otp_status == "valid":
        logs = logs.filter(otp_usage__was_valid=True)

    if otp_status == "invalid":
        logs = logs.filter(otp_usage__was_valid=False)

    if search:
        logs = logs.filter(
            Q(ticket__ticket_number__icontains=search)
            | Q(ticket__vehicle_plate__icontains=search)
            | Q(reason__icontains=search)
            | Q(otp_usage__reason__icontains=search)
            | Q(employee__username__icontains=search)
            | Q(employee__full_name__icontains=search)
            | Q(otp_usage__authorized_by_employee__username__icontains=search)
            | Q(otp_usage__authorized_by_employee__full_name__icontains=search)
            | Q(entity_type__icontains=search)
        )

    employees = Employee.objects.filter(
        is_active=True,
    ).order_by("username")

    return render(
        request,
        "audit/audit_log_list.html",
        {
            "logs": logs[:300],
            "employees": employees,
            "action_choices": AuditLog.ACTION_TYPE_CHOICES,
            "date_from": date_from,
            "date_to": date_to,
            "employee_id": employee_id,
            "action_type": action_type,
            "otp_status": otp_status,
            "search": search,
        },
    )