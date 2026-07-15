import os
import platform
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from Foundation import NSDate
    from EventKit import (
        EKAuthorizationStatusAuthorized,
        EKAuthorizationStatusNotDetermined,
        EKEntityTypeEvent,
        EKEventStore,
    )
except ImportError:
    EKEventStore = None
    EKAuthorizationStatusAuthorized = None
    EKAuthorizationStatusNotDetermined = None
    EKEntityTypeEvent = None


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def get_cors_allowed_origins() -> List[str]:
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if raw_origins:
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost",
        "http://127.0.0.1",
    ]


def create_app() -> FastAPI:
    app = FastAPI(title="Desktop Companion API", version="0.1.0")

    allowed_origins = get_cors_allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health_check() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/active-app")
    def get_active_application() -> Dict[str, Any]:
        return get_active_app_info()

    return app


app = create_app()


def get_active_app_info() -> Dict[str, Any]:
    if sys.platform != "darwin":
        return {
            "name": None,
            "bundle_id": None,
            "pid": None,
            "platform": platform.system(),
        }

    script = """
tell application \"System Events\"
    set frontApp to first application process whose frontmost is true
    set appName to name of frontApp
    set appBundleID to bundle identifier of frontApp
    set appPID to unix id of frontApp
    return appName & \"\\n\" & appBundleID & \"\\n\" & appPID
end tell
"""

    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "name": None,
            "bundle_id": None,
            "pid": None,
            "platform": platform.system(),
        }

    parts = [part.strip() for part in completed.stdout.splitlines() if part.strip()]
    if len(parts) >= 3:
        return {
            "name": parts[0],
            "bundle_id": parts[1],
            "pid": int(parts[2]),
            "platform": platform.system(),
        }

    return {
        "name": None,
        "bundle_id": None,
        "pid": None,
        "platform": platform.system(),
    }


def _create_event_store() -> Optional[EKEventStore]:
    if EKEventStore is None:
        return None

    status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
    store = EKEventStore.alloc().init()

    if status == EKAuthorizationStatusAuthorized:
        return store

    if status == EKAuthorizationStatusNotDetermined:
        access_granted = threading.Event()
        result = {"granted": False}

        def completion_handler(granted, error):
            result["granted"] = bool(granted)
            access_granted.set()

        store.requestAccessToEntityType_completion_(EKEntityTypeEvent, completion_handler)
        access_granted.wait(5.0)

        if result["granted"]:
            return store

    return None


def _format_event_date(date_value: Any) -> Optional[str]:
    try:
        return datetime.fromtimestamp(date_value.timeIntervalSince1970()).isoformat()
    except Exception:
        return None


def _is_all_day(event: Any) -> bool:
    if hasattr(event, "isAllDay"):
        return bool(event.isAllDay())
    if hasattr(event, "allDay"):
        return bool(event.allDay())
    return False


def get_calendar_filter() -> Optional[str]:
    raw_value = os.getenv("CALENDAR_FILTER", "").strip()
    return raw_value or None


def _calendar_matches_filter(calendar: Any, filter_value: Optional[str]) -> bool:
    if not filter_value:
        return True

    filter_value = filter_value.casefold()
    candidates: List[str] = []

    if calendar is None:
        return False

    title = None
    if hasattr(calendar, "title"):
        try:
            title = calendar.title()
        except Exception:
            title = None

    if title:
        candidates.append(title)

    source = None
    if hasattr(calendar, "source"):
        try:
            source = calendar.source()
        except Exception:
            source = None

    if source is not None:
        for attr_name in ("accountDescription", "title", "identifier"):
            if hasattr(source, attr_name):
                try:
                    value = getattr(source, attr_name)()
                except Exception:
                    value = None
                if value:
                    candidates.append(value)

    for attr_name in ("calendarIdentifier", "identifier"):
        if hasattr(calendar, attr_name):
            try:
                value = getattr(calendar, attr_name)()
            except Exception:
                value = None
            if value:
                candidates.append(value)

    return any(filter_value in candidate.casefold() for candidate in candidates if isinstance(candidate, str))


def _event_start_timestamp(event: Any) -> float:
    start_date = event.startDate()
    if start_date is None:
        return float("inf")
    return float(start_date.timeIntervalSince1970())


def get_next_calendar_event() -> Dict[str, Any]:
    """Return the next non-all-day calendar event for today using EventKit.

    Returns an empty dict when no event is found, Calendar access is denied,
    the platform is not macOS, or EventKit is unavailable.
    """
    if sys.platform != "darwin" or EKEventStore is None:
        return {"summary": None, "start": None, "end": None, "location": None, "calendar": None}

    store = _create_event_store()
    if store is None:
        return {"summary": None, "start": None, "end": None, "location": None, "calendar": None}

    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    start_date = NSDate.dateWithTimeIntervalSince1970_(start_of_day.timestamp())
    end_date = NSDate.dateWithTimeIntervalSince1970_(end_of_day.timestamp())

    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(start_date, end_date, None)
    events = store.eventsMatchingPredicate_(predicate)
    if not events:
        return {"summary": None, "start": None, "end": None, "location": None, "calendar": None}

    calendar_filter = get_calendar_filter()
    upcoming_events = [
        event
        for event in events
        if not _is_all_day(event)
        and _event_start_timestamp(event) >= now.timestamp()
        and _calendar_matches_filter(event.calendar(), calendar_filter)
    ]

    if not upcoming_events:
        return {"summary": None, "start": None, "end": None, "location": None, "calendar": None}

    next_event = min(upcoming_events, key=_event_start_timestamp)

    return {
        "summary": next_event.title() if next_event.title() else None,
        "start": _format_event_date(next_event.startDate()),
        "end": _format_event_date(next_event.endDate()),
        "location": next_event.location() or None,
        "calendar": next_event.calendar().title() if next_event.calendar() else None,
    }


def _event_end_timestamp(event: Any) -> float:
    end_date = event.endDate()
    if end_date is None:
        return float("inf")
    return float(end_date.timeIntervalSince1970())


def get_current_calendar_event() -> Dict[str, Any]:
    """Return the current non-all-day calendar event that is underway right now."""
    if sys.platform != "darwin" or EKEventStore is None:
        return {"summary": None, "start": None, "end": None, "location": None, "calendar": None}

    store = _create_event_store()
    if store is None:
        return {"summary": None, "start": None, "end": None, "location": None, "calendar": None}

    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    start_date = NSDate.dateWithTimeIntervalSince1970_(start_of_day.timestamp())
    end_date = NSDate.dateWithTimeIntervalSince1970_(end_of_day.timestamp())

    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(start_date, end_date, None)
    events = store.eventsMatchingPredicate_(predicate)
    if not events:
        return {"summary": None, "start": None, "end": None, "location": None, "calendar": None}

    calendar_filter = get_calendar_filter()
    current_events = [
        event
        for event in events
        if not _is_all_day(event)
        and event.startDate() is not None
        and event.endDate() is not None
        and float(event.startDate().timeIntervalSince1970()) <= now.timestamp()
        and float(event.endDate().timeIntervalSince1970()) > now.timestamp()
        and _calendar_matches_filter(event.calendar(), calendar_filter)
    ]

    if not current_events:
        return {"summary": None, "start": None, "end": None, "location": None, "calendar": None}

    current_event = min(current_events, key=_event_end_timestamp)

    return {
        "summary": current_event.title() if current_event.title() else None,
        "start": _format_event_date(current_event.startDate()),
        "end": _format_event_date(current_event.endDate()),
        "location": current_event.location() or None,
        "calendar": current_event.calendar().title() if current_event.calendar() else None,
    }


def get_calendar_debug_info() -> Dict[str, Any]:
    status_code = None
    status_name = None
    store_created = False
    exception = None

    if sys.platform != "darwin":
        status_name = "not macOS"
    elif EKEventStore is None:
        status_name = "EventKit unavailable"
    else:
        try:
            status_code = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
            if status_code == EKAuthorizationStatusAuthorized:
                status_name = "authorized"
            elif status_code == EKAuthorizationStatusNotDetermined:
                status_name = "not_determined"
            else:
                status_name = str(status_code)

            store = _create_event_store()
            store_created = store is not None
        except Exception as exc:
            exception = str(exc)

    return {
        "platform": platform.system(),
        "eventkit_available": EKEventStore is not None,
        "authorization_status": status_name,
        "store_created": store_created,
        "calendar_filter": get_calendar_filter(),
        "exception": exception,
    }


@app.get("/api/calendar-debug")
def calendar_debug() -> Dict[str, Any]:
    return get_calendar_debug_info()


@app.get("/api/calendar-next")
def next_calendar() -> Dict[str, Any]:
    """API endpoint returning the next non-all-day calendar event for today."""
    return get_next_calendar_event()


@app.get("/api/calendar-now")
def calendar_now() -> Dict[str, Any]:
    """API endpoint returning the current non-all-day calendar event underway now."""
    return get_current_calendar_event()
