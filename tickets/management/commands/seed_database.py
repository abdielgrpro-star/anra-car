from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from decimal import Decimal
import random
import hashlib

from tickets.models import Customer, Ticket
from catalog.models import Service
from cash.models import CashDay
from accounts.models import Employee


class Command(BaseCommand):
    help = "Create test tickets"

    def handle(self, *args, **options):
        fake = Faker("es_ES")

        employee = Employee.objects.first()
        cash_day = CashDay.objects.first()
        services = list(Service.objects.all())

        if not employee:
            self.stdout.write(self.style.ERROR("No hay empleados creados."))
            return

        if not cash_day:
            self.stdout.write(self.style.ERROR("No hay CashDay creado."))
            return

        if not services:
            self.stdout.write(self.style.ERROR("No hay servicios creados."))
            return

        for i in range(100):
            customer = Customer.objects.create(
                full_name=fake.name(),
                phone=fake.phone_number(),
            )

            service = random.choice(services)
            closing_code = str(random.randint(100000, 999999))

            Ticket.objects.create(
                ticket_number=f"TEST-{i + 1:05d}",
                ticket_type=Ticket.WASH,
                status=random.choice([
                    Ticket.PENDING_PAYMENT,
                    Ticket.PAID,
                    Ticket.CANCELLED,
                ]),
                customer=customer,
                service=service,
                cash_day=cash_day,
                customer_name_snapshot=customer.full_name,
                customer_phone_snapshot=customer.phone,
                vehicle_plate=fake.bothify(text="???###").upper(),
                service_name_snapshot=service.name,
                service_price_with_tax_snapshot=service.price_with_tax,
                subtotal_without_tax=Decimal("4424.78"),
                tax_rate=Decimal("0.13"),
                tax_amount=Decimal("575.22"),
                discount_amount=Decimal("0.00"),
                total_with_tax=service.price_with_tax,
                closing_code_hash=hashlib.sha256(closing_code.encode()).hexdigest(),
                closing_code_for_print=closing_code,
                created_by_employee=employee,
                paid_at=timezone.now() if random.choice([True, False]) else None,
            )

        self.stdout.write(self.style.SUCCESS("100 tickets de prueba creados."))