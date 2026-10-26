import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Contact, ContactStatus


class ContactListSerializer(serializers.ModelSerializer):
    """Short representation for GET /api/contacts/ with the fields required by the task."""

    status = serializers.StringRelatedField()

    class Meta:
        model = Contact
        fields = ["id", "first_name", "last_name", "city", "status", "created_at"]


class ContactSerializer(serializers.ModelSerializer):
    """Full representation for contact details, create and update."""

    # Statuses are sent and returned by name, e.g. "status": "nowy"
    status = serializers.SlugRelatedField(slug_field="name", queryset=ContactStatus.objects.all())

    class Meta:
        model = Contact
        fields = ["id", "first_name", "last_name", "phone", "email", "city", "status", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        # DRF does not call Model.full_clean(), so run it here. This applies the same
        # normalization and uniqueness checks as the HTML form (see Contact.clean()).
        instance = copy.copy(self.instance) if self.instance else Contact()
        for field, value in attrs.items():
            setattr(instance, field, value)
        try:
            instance.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict)
        # Return the normalized values, e.g. the phone number without spaces
        return {field: getattr(instance, field) for field in attrs}