# EventHub — Django REST Framework API

EventHub is a simple event ticketing backend. It supports event browsing, seat reservations, cancellations, filtering, and request logging.

## Requirements
- Python 3.10+
- pip

## Run locally

```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# Windows Command Prompt
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 2. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Run automated tests
python manage.py test

# 5. Start the development server
python manage.py runserver
```

The API base URL is `http://127.0.0.1:8000/api/`. SQLite is used by default; Django creates `db.sqlite3` when migrations run.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/events/` | List events |
| POST | `/api/events/` | Create an event |
| GET | `/api/events/{id}/` | Retrieve one event |
| PUT/PATCH | `/api/events/{id}/` | Update an event |
| DELETE | `/api/events/{id}/` | Delete an event |
| GET | `/api/events/?status=upcoming` | Filter by event status |
| GET | `/api/events/?venue=chennai` | Case-insensitive venue search |
| GET | `/api/reservations/` | List reservations |
| POST | `/api/reservations/` | Reserve seats |
| GET | `/api/reservations/{id}/` | Retrieve a reservation |
| PUT/PATCH | `/api/reservations/{id}/` | Update a reservation |
| DELETE | `/api/reservations/{id}/` | Delete a reservation |
| GET | `/api/reservations/?event_id=1` | Filter reservations by event |
| POST | `/api/reservations/{id}/cancel/` | Cancel a reservation and restore seats |

## Example requests

### Create an event
`POST /api/events/`

```json
{
  "title": "PyCon India",
  "venue": "NIMHANS Convention Centre, Bangalore",
  "date": "2027-09-20",
  "total_seats": 500,
  "available_seats": 500,
  "status": "upcoming"
}
```

### Reserve seats
`POST /api/reservations/`

```json
{
  "event": 1,
  "attendee_name": "Priya Sharma",
  "attendee_email": "priya@example.com",
  "seats_reserved": 2
}
```

A successful reservation returns `201 Created` and decreases the event's `available_seats`. If there are insufficient seats, the API returns `400 Bad Request`.

### Cancel a reservation
`POST /api/reservations/1/cancel/`

No request body is required. The response contains the reservation with `status: "cancelled"` and the event's available-seat count is restored. Repeated cancellation returns `400 Bad Request`.

## Design decision: safe seat reservation

Seat deduction and reservation creation are performed in a database transaction. A conditional `UPDATE` subtracts seats only when the event is reservable and has enough seats remaining. This avoids the classic read-then-write race that can oversell the final seat on a database that supports the required write semantics. SQLite serializes writes; for a production deployment, use PostgreSQL and test concurrent requests under the intended isolation and locking strategy.

Cancellation also wraps the status change and seat restoration in a transaction, so the same reservation cannot be successfully cancelled twice and return seats twice.

## Request logging

`events.middleware.RequestLoggingMiddleware` logs the HTTP method, path, response status, and elapsed time to the server terminal.

## Tests

```bash
python manage.py test
```

The test suite covers event listing/filtering, reservation seat deduction, overbooking, cancellation, duplicate cancellation, and reservation filtering.

## Postman
Import `postman/EventHub.postman_collection.json` into Postman. Set `base_url` to `http://127.0.0.1:8000` and run requests in order. The collection includes successful reservation, overbooking, and cancellation requests. Capture your own screenshots from Postman after running them; screenshots are not fabricated or included as if they were real executions.

## Notes
- This is a learning project and uses `DEBUG = True` with a development-only secret key. Do not deploy these settings to production.
- The sample event date is illustrative; use a future date when creating your own event.
