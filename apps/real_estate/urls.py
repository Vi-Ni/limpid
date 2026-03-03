from django.urls import path

from . import views

app_name = "real_estate"

urlpatterns = [
    path("", views.property_list, name="list"),
    path("create/", views.property_create, name="create"),
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/mark-read/", views.mark_notifications_read, name="mark_all_read"),
    path("<int:pk>/", views.property_detail, name="detail"),
    path("<int:pk>/edit/", views.property_edit, name="edit"),
    path("<int:pk>/expense/", views.add_expense, name="add_expense"),
    path("<int:pk>/expense/<int:expense_id>/edit/", views.edit_expense, name="edit_expense"),
    path("<int:pk>/expense/<int:expense_id>/delete/", views.delete_expense, name="delete_expense"),
    path("<int:pk>/valuation/", views.add_valuation, name="add_valuation"),
    path("<int:pk>/valuation/<int:valuation_id>/edit/", views.edit_valuation, name="edit_valuation"),
    path("<int:pk>/valuation/<int:valuation_id>/delete/", views.delete_valuation, name="delete_valuation"),
    path("<int:pk>/tax/", views.add_tax, name="add_tax"),
    path("<int:pk>/tax/<int:tax_id>/edit/", views.edit_tax, name="edit_tax"),
    path("<int:pk>/tax/<int:tax_id>/delete/", views.delete_tax, name="delete_tax"),
    path("<int:pk>/mortgage/<int:mortgage_id>/amortization/", views.amortization_view, name="amortization"),
    path("<int:pk>/sale-simulator/", views.sale_simulator, name="sale_simulator"),
    path("<int:pk>/invite/", views.invite_co_owner, name="invite"),
    path("<int:pk>/remove-owner/<int:ownership_id>/", views.remove_co_owner, name="remove_co_owner"),
    path("invite/<str:token>/accept/", views.accept_invitation, name="accept_invite"),
    path("<int:pk>/ownership-periods/", views.manage_ownership_periods, name="ownership_periods"),
    path("currency/toggle/", views.toggle_currency, name="toggle_currency"),
]
