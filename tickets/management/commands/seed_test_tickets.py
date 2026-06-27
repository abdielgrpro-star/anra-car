import random
import string
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from cash.models import CashDay
from catalog.models import Service
from payments.models import Payment
from tickets.models import Ticket
from tickets.utils import calculate_parking_total, calculate_tax_from_total


class Command(BaseCommand):
    help = "Crea tickets falsos de prueba para una o varias fechas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--day",
            action="append",
            required=True,
            help="Formato: YYYY-MM-DD:CANTIDAD. Ejemplo: --day 2026-06-20:20",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        employee = User.objects.filter(is_active=True).first()

        if not employee:
            self.stdout.write(
                self.style.ERROR("No hay empleados activos para crear tickets.")
            )
            return

        wash_services = list(
            Service.objects.filter(
                service_type=Service.WASH,
                is_active=True,
            )
        )

        parking_services = list(
            Service.objects.filter(
                service_type=Service.PARKING,
                is_active=True,
            )
        )

        if not wash_services:
            self.stdout.write(
                self.style.ERROR("No hay servicios de lavado activos.")
            )
            return

        if not parking_services:
            self.stdout.write(
                self.style.ERROR("No hay servicio de parqueo activo.")
            )
            return

        total_created = 0

        for day_config in options["day"]:
            try:
                date_text, count_text = day_config.split(":")
                business_date = datetime.strptime(date_text, "%Y-%m-%d").date()
                ticket_count = int(count_text)
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(
                        f"Formato inválido: {day_config}. Use YYYY-MM-DD:CANTIDAD"
                    )
                )
                continue

            cash_day, created = CashDay.objects.get_or_create(
                business_date=business_date,
                defaults={
                    "status": CashDay.CLOSED,
                    "closed_automatically": True,
                },
            )

            opened_at = timezone.make_aware(
                datetime.combine(business_date, time(7, 0))
            )

            closed_at = timezone.make_aware(
                datetime.combine(business_date, time(21, 0))
            )

            cash_day.opened_at = opened_at
            cash_day.closed_at = closed_at
            cash_day.status = CashDay.CLOSED
            cash_day.closed_automatically = True
            cash_day.save(
                update_fields=[
                    "opened_at",
                    "closed_at",
                    "status",
                    "closed_automatically",
                    "updated_at",
                ]
            )

            for index in range(1, ticket_count + 1):
                ticket_type = random.choice([Ticket.WASH, Ticket.PARKING])

                created_at = self.random_datetime_for_day(business_date)
                paid_at = created_at + timedelta(minutes=random.randint(10, 180))

                if paid_at.date() != business_date:
                    paid_at = timezone.make_aware(
                        datetime.combine(business_date, time(20, 45))
                    )

                if ticket_type == Ticket.WASH:
                    ticket = self.create_wash_ticket(
                        cash_day=cash_day,
                        employee=employee,
                        service=random.choice(wash_services),
                        business_date=business_date,
                        index=index,
                        created_at=created_at,
                        paid_at=paid_at,
                    )
                else:
                    ticket = self.create_parking_ticket(
                        cash_day=cash_day,
                        employee=employee,
                        service=random.choice(parking_services),
                        business_date=business_date,
                        index=index,
                        created_at=created_at,
                        paid_at=paid_at,
                    )

                total_created += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Creados {ticket_count} tickets para {business_date}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Proceso terminado. Total de tickets creados: {total_created}"
            )
        )

    def random_datetime_for_day(self, business_date):
        hour = random.randint(7, 20)
        minute = random.randint(0, 59)

        return timezone.make_aware(
            datetime.combine(
                business_date,
                time(hour, minute),
            )
        )

    def random_code(self):
        alphabet = string.ascii_uppercase + string.digits
        return "".join(random.choice(alphabet) for _ in range(12))

    def random_plate(self):
        letters = "".join(random.choice(string.ascii_uppercase) for _ in range(3))
        numbers = random.randint(100, 999)
        return f"{letters}{numbers}"

    def random_customer_name(self):
        names = [
            "Carlos Mora",
            "María López",
            "Juan Pérez",
            "Andrea Castro",
            "Luis Rodríguez",
            "Gabriela Sánchez",
            "Cliente Prueba",
            "Admin Test",
            "Pedro Vargas",
            "Sofía Ramírez",
        ]

        return random.choice(names)

    def random_payment_method(self):
        return random.choice([Payment.CASH, Payment.SINPE])

    def create_wash_ticket(
        self,
        *,
        cash_day,
        employee,
        service,
        business_date,
        index,
        created_at,
        paid_at,
    ):
        closing_code = self.random_code()

        tax_data = calculate_tax_from_total(
            total_with_tax=service.price_with_tax,
            tax_rate=service.tax_rate,
        )

        ticket_number = f"TST-L-{business_date.strftime('%Y%m%d')}-{index:04d}"

        ticket = Ticket.objects.create(
            ticket_number=ticket_number,
            ticket_type=Ticket.WASH,
            status=Ticket.PAID,
            customer=None,
            service=service,
            cash_day=cash_day,
            customer_name_snapshot=self.random_customer_name(),
            customer_phone_snapshot=f"8{random.randint(1000000, 9999999)}",
            vehicle_plate=self.random_plate(),
            service_name_snapshot=service.name,
            service_price_with_tax_snapshot=service.price_with_tax,
            subtotal_without_tax=tax_data["subtotal_without_tax"],
            tax_rate=service.tax_rate,
            tax_amount=tax_data["tax_amount"],
            discount_amount=Decimal("0.00"),
            total_with_tax=tax_data["total_with_tax"],
            closing_code_hash=make_password(closing_code),
            closing_code_for_print=closing_code,
            created_by_employee=employee,
            updated_by_employee=employee,
            paid_at=paid_at,
            print_count=1,
            last_printed_at=created_at,
            last_printed_by_employee=employee,
        )

        Ticket.objects.filter(id=ticket.id).update(
            created_at=created_at,
            updated_at=paid_at,
            paid_at=paid_at,
            last_printed_at=created_at,
        )

        payment_method = self.random_payment_method()

        payment = Payment.objects.create(
            ticket=ticket,
            cash_day=cash_day,
            received_by_employee=employee,
            payment_method=payment_method,
            amount=ticket.total_with_tax,
            sinpe_reference=(
                f"SINPE-{random.randint(10000, 99999)}"
                if payment_method == Payment.SINPE
                else ""
            ),
        )

        Payment.objects.filter(id=payment.id).update(
            created_at=paid_at,
        )

        return ticket

    def create_parking_ticket(
        self,
        *,
        cash_day,
        employee,
        service,
        business_date,
        index,
        created_at,
        paid_at,
    ):
        closing_code = self.random_code()

        parking_minutes = random.randint(30, 240)

        parking_total = calculate_parking_total(
            minutes=parking_minutes,
            first_hour_price=service.price_with_tax,
            block_price=Decimal("500.00"),
            block_minutes=30,
        )

        tax_data = calculate_tax_from_total(
            total_with_tax=parking_total,
            tax_rate=service.tax_rate,
        )

        parking_entry_at = paid_at - timedelta(minutes=parking_minutes)

        ticket_number = f"TST-P-{business_date.strftime('%Y%m%d')}-{index:04d}"

        ticket = Ticket.objects.create(
            ticket_number=ticket_number,
            ticket_type=Ticket.PARKING,
            status=Ticket.PAID,
            customer=None,
            service=service,
            cash_day=cash_day,
            customer_name_snapshot=self.random_customer_name(),
            customer_phone_snapshot=f"8{random.randint(1000000, 9999999)}",
            vehicle_plate=self.random_plate(),
            service_name_snapshot=service.name,
            service_price_with_tax_snapshot=service.price_with_tax,
            subtotal_without_tax=tax_data["subtotal_without_tax"],
            tax_rate=service.tax_rate,
            tax_amount=tax_data["tax_amount"],
            discount_amount=Decimal("0.00"),
            total_with_tax=tax_data["total_with_tax"],
            closing_code_hash=make_password(closing_code),
            closing_code_for_print=closing_code,
            parking_entry_at=parking_entry_at,
            parking_exit_at=paid_at,
            parking_minutes=parking_minutes,
            parking_first_hour_price_snapshot=service.price_with_tax,
            parking_block_price_snapshot=Decimal("500.00"),
            parking_block_minutes_snapshot=30,
            created_by_employee=employee,
            updated_by_employee=employee,
            paid_at=paid_at,
            print_count=1,
            last_printed_at=created_at,
            last_printed_by_employee=employee,
        )

        Ticket.objects.filter(id=ticket.id).update(
            created_at=created_at,
            updated_at=paid_at,
            paid_at=paid_at,
            last_printed_at=created_at,
        )

        payment_method = self.random_payment_method()

        payment = Payment.objects.create(
            ticket=ticket,
            cash_day=cash_day,
            received_by_employee=employee,
            payment_method=payment_method,
            amount=ticket.total_with_tax,
            sinpe_reference=(
                f"SINPE-{random.randint(10000, 99999)}"
                if payment_method == Payment.SINPE
                else ""
            ),
        )

        Payment.objects.filter(id=payment.id).update(
            created_at=paid_at,
        )

        return ticket