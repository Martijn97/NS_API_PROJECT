from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Departure:
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
    return datetime.fromisoformat(value) if value else None


def _to_departure(raw: dict) -> Departure:
    planned = _parse_dt(raw["plannedDateTime"])
    actual = _parse_dt(raw.get("actualDateTime"))
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
        track_changed=bool(
            planned_track and actual_track and planned_track != actual_track
        ),
        cancelled=raw.get("cancelled", False),
    )


def parse_departures(payload: dict) -> list[Departure]:
    return [_to_departure(d) for d in payload["payload"]["departures"]]