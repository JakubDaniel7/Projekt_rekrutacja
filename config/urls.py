from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from contacts.api import ContactViewSet, weather_view

# The router generates /api/contacts/ and /api/contacts/{id}/ for the ViewSet
router = DefaultRouter()
router.register("contacts", ContactViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/weather/", weather_view, name="weather"),
    path("api/", include(router.urls)),
    path("", include("contacts.urls")),
]