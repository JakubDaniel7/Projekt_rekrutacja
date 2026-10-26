from datetime import timedelta

from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, FormView, ListView, TemplateView, UpdateView

from .csv_io import CsvImportError, export_contacts, import_contacts
from .forms import ContactForm, CsvImportForm
from .models import Contact, ContactStatus

import json

# Allowed ?sort= values: label shown in the UI and the ORDER BY fields
SORT_OPTIONS = {
    "last_name": ("Nazwisko A–Z", ["last_name", "first_name"]),
    "-last_name": ("Nazwisko Z–A", ["-last_name", "-first_name"]),
    "-created_at": ("Najnowsze", ["-created_at"]),
    "created_at": ("Najstarsze", ["created_at"]),
}
DEFAULT_SORT = "last_name"
TOP_CITIES = 8  # the remaining cities are grouped as "Pozostałe" on the dashboard


class ContactListView(ListView):
    model = Contact
    context_object_name = "contacts"
    paginate_by = 10

    def get_sort(self):
        sort = self.request.GET.get("sort")
        # Only whitelisted values may reach ORDER BY
        return sort if sort in SORT_OPTIONS else DEFAULT_SORT

    def get_queryset(self):
        # Load each contact's status in the same query instead of one extra query per row
        queryset = Contact.objects.select_related("status")

        # Every word must appear somewhere in the contact; search_text is stored lowercase
        for word in self.request.GET.get("q", "").lower().split():
            queryset = queryset.filter(search_text__contains=word)

        return queryset.order_by(*SORT_OPTIONS[self.get_sort()][1])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["sort"] = self.get_sort()
        context["sort_options"] = {key: label for key, (label, _) in SORT_OPTIONS.items()}
        return context

    def get_template_names(self):
        # htmx requests (live search, sorting, paging) only need the table, not the whole page
        if self.request.headers.get("HX-Request"):
            return ["contacts/_contact_table.html"]
        return ["contacts/contact_list.html"]


class ContactCreateView(SuccessMessageMixin, CreateView):
    model = Contact
    form_class = ContactForm
    success_url = reverse_lazy("contacts:list")
    success_message = "Dodano kontakt: %(first_name)s %(last_name)s."


class ContactUpdateView(SuccessMessageMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    success_url = reverse_lazy("contacts:list")
    success_message = "Zapisano zmiany: %(first_name)s %(last_name)s."


class ContactDeleteView(SuccessMessageMixin, DeleteView):
    model = Contact
    success_url = reverse_lazy("contacts:list")

    def get_success_message(self, cleaned_data):
        # The confirmation form has no fields, so build the message from the deleted object
        return f"Usunięto kontakt: {self.object}."

    def form_valid(self, form):
        if not self.request.headers.get("HX-Request"):
            return super().form_valid(form)  # regular form: delete, then redirect to the list

        # htmx: delete and answer with an empty body - the row is replaced by "nothing",
        # and the HX-Trigger header makes the page show a toast (see app.js)
        message = self.get_success_message({})
        self.object.delete()
        response = HttpResponse("")
        response["HX-Trigger"] = json.dumps({"showMessage": {"text": message, "level": "success"}})
        return response


class ContactImportView(FormView):
    template_name = "contacts/contact_import.html"
    form_class = CsvImportForm

    def form_valid(self, form):
        try:
            result = import_contacts(form.cleaned_data["file"])
        except CsvImportError as error:
            form.add_error("file", str(error))
            return self.form_invalid(form)
        # Show the report on the same page, with an empty form ready for the next file
        return self.render_to_response(self.get_context_data(form=self.form_class(), result=result))


def contact_export_view(request):
    filename = f"kontakty_{timezone.localdate():%Y-%m-%d}.csv"
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # Byte order mark, so Excel recognizes UTF-8 and shows Polish letters correctly
    response.write("\ufeff")
    export_contacts(Contact.objects.select_related("status"), response)
    return response


class DashboardView(TemplateView):
    template_name = "contacts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cities = list(
            Contact.objects.values("city").annotate(count=Count("id")).order_by("-count", "city")
        )
        city_chart = [{"label": row["city"], "count": row["count"]} for row in cities[:TOP_CITIES]]
        other_count = sum(row["count"] for row in cities[TOP_CITIES:])
        if other_count:
            city_chart.append({"label": "Pozostałe", "count": other_count, "other": True})

        statuses = ContactStatus.objects.annotate(count=Count("contacts")).order_by("id")
        status_chart = [{"label": s.name, "count": s.count, "color": s.color} for s in statuses]

        week_ago = timezone.now() - timedelta(days=7)
        context.update(
            total=Contact.objects.count(),
            city_count=len(cities),
            added_last_week=Contact.objects.filter(created_at__gte=week_ago).count(),
            city_chart=city_chart,
            status_chart=status_chart,
        )
        return context