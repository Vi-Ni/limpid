from django.urls import path

from . import views

app_name = "real_estate"

urlpatterns = [
    path("", views.property_list, name="list"),
    path("create/", views.property_create, name="create"),
    path("<int:pk>/", views.property_detail, name="detail"),
    path("<int:pk>/edit/", views.property_edit, name="edit"),
    path("<int:pk>/expense/", views.add_expense, name="add_expense"),
    path("<int:pk>/valuation/", views.add_valuation, name="add_valuation"),
    path("<int:pk>/tax/", views.add_tax, name="add_tax"),
    path("<int:pk>/mortgage/<int:mortgage_id>/amortization/", views.amortization_view, name="amortization"),
    path("<int:pk>/sale-simulator/", views.sale_simulator, name="sale_simulator"),
    path("<int:pk>/invite/", views.invite_co_owner, name="invite"),
    path("invite/<str:token>/accept/", views.accept_invitation, name="accept_invite"),
    path("<int:pk>/ownership-periods/", views.manage_ownership_periods, name="ownership_periods"),
]
