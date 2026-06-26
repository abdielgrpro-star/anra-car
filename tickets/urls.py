from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("wash/create/", views.create_wash_ticket, name="create_wash_ticket"),
    path("wash/pending/", views.pending_wash_tickets, name="pending_wash_tickets"),
    path("wash/<int:ticket_id>/charge/", views.charge_wash_ticket, name="charge_wash_ticket"),
    path("wash/<int:ticket_id>/", views.wash_ticket_detail, name="wash_ticket_detail"),

    path("parking/create/", views.create_parking_ticket, name="create_parking_ticket"),
    path("parking/active/", views.active_parking_tickets, name="active_parking_tickets"),
    path("parking/<int:ticket_id>/charge/", views.charge_parking_ticket, name="charge_parking_ticket"),
    path("parking/<int:ticket_id>/", views.parking_ticket_detail, name="parking_ticket_detail"),
]