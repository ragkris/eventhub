from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from .models import Event, Reservation


class EventSerializer(serializers.ModelSerializer):
    reservations_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "title", "venue", "date", "total_seats",
            "available_seats", "status", "created_at", "reservations_count",
        ]
        read_only_fields = ["id", "created_at", "reservations_count"]

    def get_reservations_count(self, obj):
        return obj.reservations.filter(status="confirmed").count()

    def validate(self, data):
        total_seats = data.get("total_seats", getattr(self.instance, "total_seats", None))
        available_seats = data.get("available_seats", getattr(self.instance, "available_seats", None))
        if total_seats is not None and available_seats is not None and available_seats > total_seats:
            raise serializers.ValidationError({
                "available_seats": "available_seats cannot exceed total_seats."
            })
        return data


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            "id", "event", "attendee_name", "attendee_email",
            "seats_reserved", "status", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_seats_reserved(self, value):
        if value < 1:
            raise serializers.ValidationError("Must reserve at least 1 seat.")
        return value

    def validate(self, data):
        event = data.get("event")
        seats = data.get("seats_reserved", 0)
        if event is not None:
            if event.status not in ("upcoming", "ongoing"):
                raise serializers.ValidationError(
                    {"event": f"Cannot reserve seats for a {event.status} event."}
                )
            # Friendly early validation. The atomic conditional update in create()
            # is the authoritative check when multiple requests arrive concurrently.
            if seats > event.available_seats:
                raise serializers.ValidationError(
                    {"non_field_errors": [f"Only {event.available_seats} seat(s) available."]}
                )
        return data

    def create(self, validated_data):
        # A conditional database update prevents overselling if requests race.
        # Reservation creation and seat deduction are committed/rolled back together.
        with transaction.atomic():
            event = validated_data["event"]
            seats = validated_data["seats_reserved"]
            updated = Event.objects.filter(
                pk=event.pk,
                status__in=["upcoming", "ongoing"],
                available_seats__gte=seats,
            ).update(available_seats=F("available_seats") - seats)

            if updated == 0:
                event.refresh_from_db()
                if event.status not in ("upcoming", "ongoing"):
                    raise serializers.ValidationError(
                        {"event": f"Cannot reserve seats for a {event.status} event."}
                    )
                raise serializers.ValidationError({
                    "non_field_errors": [f"Only {event.available_seats} seat(s) available."]
                })

            reservation = Reservation.objects.create(**validated_data)
            return reservation
