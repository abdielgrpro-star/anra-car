from django.urls import path

from . import views

app_name = "cash"

urlpatterns = [
    path("today/", views.cash_day_detail, name="cash_day_detail"),
    path("today/close/", views.close_cash_day_confirm, name="close_cash_day_confirm"),

    path("reports/", views.cash_day_report_list, name="cash_day_report_list"),
    path("reports/export/", views.cash_day_report_export_csv, name="cash_day_report_export_csv"),
]