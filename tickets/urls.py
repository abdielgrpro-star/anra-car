from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("wash/create/", views.create_wash_ticket, name="create_wash_ticket"),
    path("wash/pending/", views.pending_wash_tickets, name="pending_wash_tickets"),
    path("wash/<int:ticket_id>/charge/", views.charge_wash_ticket, name="charge_wash_ticket"),
    path("wash/<int:ticket_id>/", views.wash_ticket_detail, name="wash_ticket_detail"),
]