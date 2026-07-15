from datetime import datetime, timedelta

from fastapi.testclient import TestClient

import app.main as main_module


client = TestClient(main_module.app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_active_app_endpoint_returns_expected_shape():
    response = client.get("/api/active-app")

    assert response.status_code == 200
    payload = response.json()
    assert "name" in payload
    assert "bundle_id" in payload
    assert "pid" in payload
    assert "platform" in payload


def test_calendar_now_endpoint_returns_expected_shape(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "get_current_calendar_event",
        lambda: {
            "summary": None,
            "start": None,
            "end": None,
            "location": None,
            "calendar": None,
        },
    )

    response = client.get("/api/calendar-now")

    assert response.status_code == 200
    assert response.json() == {
        "summary": None,
        "start": None,
        "end": None,
        "location": None,
        "calendar": None,
    }


def test_next_calendar_endpoint_returns_event_shape(monkeypatch):
    class FakeDate:
        def __init__(self, value):
            self._value = value

        def timeIntervalSince1970(self):
            return self._value.timestamp()

    class FakeCalendar:
        def __init__(self, title):
            self._title = title

        def title(self):
            return self._title

    class FakeEvent:
        def __init__(self, title, start, end, location, calendar):
            self._title = title
            self._start = start
            self._end = end
            self._location = location
            self._calendar = calendar

        def startDate(self):
            return self._start

        def endDate(self):
            return self._end

        def title(self):
            return self._title

        def location(self):
            return self._location

        def calendar(self):
            return self._calendar

        def isAllDay(self):
            return False

    class FakeStore:
        @classmethod
        def authorizationStatusForEntityType_(cls, entity_type):
            return 1

        @classmethod
        def alloc(cls):
            return cls()

        def init(self):
            return self

        def requestAccessToEntityType_completion_(self, entity_type, callback):
            callback(True, None)

        def predicateForEventsWithStartDate_endDate_calendars_(self, start_date, end_date, calendars):
            return (start_date, end_date)

        def eventsMatchingPredicate_(self, predicate):
            start_time = datetime.now() + timedelta(hours=1)
            end_time = datetime.now() + timedelta(hours=2)
            return [
                FakeEvent(
                    "Standup",
                    FakeDate(start_time),
                    FakeDate(end_time),
                    "Office",
                    FakeCalendar("Work"),
                )
            ]

    monkeypatch.setattr(main_module.sys, "platform", "darwin", raising=False)
    monkeypatch.setattr(main_module, "EKEventStore", FakeStore, raising=False)
    monkeypatch.setattr(main_module, "EKAuthorizationStatusAuthorized", 1, raising=False)
    monkeypatch.setattr(main_module, "EKAuthorizationStatusNotDetermined", 0, raising=False)
    monkeypatch.setattr(main_module, "EKEntityTypeEvent", object(), raising=False)
    monkeypatch.setattr(main_module, "NSDate", type("NSDate", (), {"dateWithTimeIntervalSince1970_": classmethod(lambda cls, timestamp: timestamp)}), raising=False)

    response = client.get("/api/calendar-next")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "Standup"
    assert payload["location"] == "Office"
    assert payload["calendar"] == "Work"
    assert payload["start"] is not None
    assert payload["end"] is not None


def test_cors_origin_is_configured_from_environment(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://dashboard.example.com,https://admin.example.com",
    )

    app = main_module.create_app()
    test_client = TestClient(app)
    response = test_client.options(
        "/health",
        headers={
            "Origin": "https://dashboard.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://dashboard.example.com"


def test_localhost_origin_is_allowed_by_default(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    app = main_module.create_app()
    test_client = TestClient(app)
    response = test_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
