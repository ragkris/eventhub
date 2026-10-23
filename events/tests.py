from datetime import date, timedelta
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Event, Reservation


class EventHubAPITests(APITestCase):
    def setUp(self):
        self.event = Event.objects.create(
            title="Test Conference",
            venue="Chennai Trade Centre",
            date=date.today() + timedelta(days=30),
            total_seats=3,
            available_seats=3,
            status="upcoming",
        )

    def test_create_event_and_list(self):
        response = self.client.get("/api/events/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_event_filters(self):
        response = self.client.get("/api/events/?status=upcoming&venue=chennai")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_reservation_deducts_seats(self):
        response = self.client.post("/api/reservations/", {
            "event": self.event.id,
            "attendee_name": "Priya Sharma",
            "attendee_email": "priya@example.com",
            "seats_reserved": 2,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_seats, 1)

    def test_overbooking_returns_400(self):
        response = self.client.post("/api/reservations/", {
            "event": self.event.id,
            "attendee_name": "Priya Sharma",
            "attendee_email": "priya@example.com",
            "seats_reserved": 4,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_restores_seats_and_cannot_cancel_twice(self):
        reservation = Reservation.objects.create(
            event=self.event, attendee_name="Priya Sharma",
            attendee_email="priya@example.com", seats_reserved=2,
        )
        Event.objects.filter(pk=self.event.pk).update(available_seats=1)
        response = self.client.post(f"/api/reservations/{reservation.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.available_seats, 3)
        second = self.client.post(f"/api/reservations/{reservation.id}/cancel/")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reservation_filter_by_event_id(self):
        Reservation.objects.create(
            event=self.event, attendee_name="Priya Sharma",
            attendee_email="priya@example.com", seats_reserved=1,
        )
        response = self.client.get(f"/api/reservations/?event_id={self.event.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
