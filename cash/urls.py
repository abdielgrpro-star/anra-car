from django.urls import path

from . import views

app_name = "cash"

urlpatterns = [
    path("today/", views.cash_day_detail, name="cash_day_detail"),
]