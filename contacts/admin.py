from django.contrib import admin

from .models import Contact, ContactStatus


@admin.register(ContactStatus)
class ContactStatusAdmin(admin.ModelAdmin):
    list_display = ["name", "color"]
    list_editable = ["color"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["last_name", "first_name", "phone", "email", "city", "status", "created_at"]
    list_filter = ["status", "city"]
    search_fields = ["first_name", "last_name", "email", "phone", "city"]
    ordering = ["-created_at"]