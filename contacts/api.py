import logging

from django.http import JsonResponse
from rest_framework import viewsets

from .models import Contact
from .serializers import ContactListSerializer, ContactSerializer
from .weather import WeatherUnavailable, get_weather

logger = logging.getLogger(__name__)


class ContactViewSet(viewsets.ModelViewSet):
    """
    REST API for contacts.

    GET    /api/contacts/       - list of contacts
    POST   /api/contacts/       - create a contact
    GET    /api/contacts/{id}/  - contact details
    PUT    /api/contacts/{id}/  - update a contact
    PATCH  /api/contacts/{id}/  - partial update
    DELETE /api/contacts/{id}/  - delete a contact
    """

    queryset = Contact.objects.select_related("status")

    def get_serializer_class(self):
        # The list returns only the fields required by the task; everything else uses the full serializer
        if self.action == "list":
            return ContactListSerializer
        return ContactSerializer


def weather_view(request):
    """GET /api/weather/?city=... - current weather for a city, used by the contact list."""
    city = request.GET.get("city", "").strip()
    if not city:
        return JsonResponse({"error": "Podaj parametr city."}, status=400)

    try:
        weather = get_weather(city)
    except WeatherUnavailable:
        logger.warning("Weather lookup failed for %r", city, exc_info=True)
        return JsonResponse({"error": "Serwis pogodowy jest chwilowo niedostępny."}, status=503)

    if weather is None:
        return JsonResponse({"error": "Nie znaleziono miasta."}, status=404)
    return JsonResponse(weather)