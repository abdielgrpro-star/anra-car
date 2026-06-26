from django.urls import path

from . import views

app_name = "cash"

urlpatterns = [
    path("today/", views.cash_day_detail, name="cash_day_detail"),
    path("today/close/", views.close_cash_day_confirm, name="close_cash_day_confirm"),
]