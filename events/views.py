from django.db import transaction
from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Event, Reservation
from .serializers import EventSerializer, ReservationSerializer


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        queryset = Event.objects.all()
        status_param = self.request.query_params.get("status")
        venue_param = self.request.query_params.get("venue")
        if status_param:
            queryset = queryset.filter(status=status_param)
        if venue_param:
            queryset = queryset.filter(venue__icontains=venue_param)
        return queryset


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer

    def get_queryset(self):
        queryset = Reservation.objects.select_related("event").all()
        event_id = self.request.query_params.get("event_id")
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return queryset

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        # Lock the reservation row where supported, and update both records atomically.
        with transaction.atomic():
            reservation = self.get_queryset().select_for_update().get(pk=self.get_object().pk)
            if reservation.status == "cancelled":
                return Response({"error": "Already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

            Event.objects.filter(pk=reservation.event_id).update(
                available_seats=F("available_seats") + reservation.seats_reserved
            )
            reservation.status = "cancelled"
            reservation.save(update_fields=["status"])

        reservation.refresh_from_db()
        return Response(self.get_serializer(reservation).data, status=status.HTTP_200_OK)
