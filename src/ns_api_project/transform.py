"""Turn the raw NS JSON payload into typed `Departure` records.

Pure functions only: no I/O, no network. That keeps this layer fast to test and
independent of whatever the API layer does.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Departure:
    """One departure, normalised into the fields we actually care about.

    Frozen so records can't be mutated after parsing; `aggregate` only reads.
    """

    destination: str
    train_category: str
    planned_departure: datetime
    actual_departure: datetime | None
    delay_minutes: float
    planned_track: str | None
    actual_track: str | None
    track_changed: bool
    cancelled: bool


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an NS timestamp, tolerating a missing/null value."""
    # NS sends ISO-8601 with a +0200 style offset; fromisoformat handles it on 3.11+.
    return datetime.fromisoformat(value) if value else None


def _to_departure(raw: dict) -> Departure:
    """Map one raw departure dict onto a `Departure`."""
    # plannedDateTime is always present; actualDateTime is absent for cancelled
    # trains and for departures the NS has no realtime estimate for yet.
    planned = _parse_dt(raw["plannedDateTime"])
    actual = _parse_dt(raw.get("actualDateTime"))

    # No realtime timestamp means we have nothing to measure against, so the
    # delay is reported as 0.0 rather than guessed.
    delay = (actual - planned).total_seconds() / 60 if actual else 0.0

    planned_track = raw.get("plannedTrack")
    actual_track = raw.get("actualTrack")

    return Departure(
        destination=raw["direction"],
        train_category=raw["product"]["shortCategoryName"],
        planned_departure=planned,
        actual_departure=actual,
        delay_minutes=delay,
        planned_track=planned_track,
        actual_track=actual_track,
        # Only a real change counts: if either track is unknown we can't tell.
        track_changed=bool(
            planned_track and actual_track and planned_track != actual_track
        ),
        cancelled=raw.get("cancelled", False),
    )


def parse_departures(payload: dict) -> list[Departure]:
    """Parse a full API response into a list of `Departure` records.

    Raises:
        KeyError: if the payload does not have the expected envelope shape,
            which is deliberate — a silent empty list would hide API changes.
    """
    return [_to_departure(d) for d in payload["payload"]["departures"]]