from django.urls import path

from . import views

app_name = "contacts"

urlpatterns = [
    path("", views.ContactListView.as_view(), name="list"),
    path("new/", views.ContactCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.ContactUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.ContactDeleteView.as_view(), name="delete"),
    path("import/", views.ContactImportView.as_view(), name="import"),
    path("export/", views.contact_export_view, name="export"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]