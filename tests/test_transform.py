from datetime import datetime

from ns_api_project.transform import parse_departures

PAYLOAD = {
    "payload": {
        "departures": [
            {
                "direction": "Amsterdam Centraal",
                "plannedDateTime": "2026-07-31T09:30:00+0200",
                "actualDateTime": "2026-07-31T09:33:00+0200",
                "plannedTrack": "5",
                "actualTrack": "8",
                "cancelled": False,
                "product": {"shortCategoryName": "IC"},
            },
            {
                "direction": "Den Haag Centraal",
                "plannedDateTime": "2026-07-31T09:45:00+0200",
                "plannedTrack": "11",
                "cancelled": True,
                "product": {"shortCategoryName": "SPR"},
            },
        ]
    }
}


def test_parses_delay_and_track_change():
    departures = parse_departures(PAYLOAD)
    first = departures[0]

    assert first.destination == "Amsterdam Centraal"
    assert first.delay_minutes == 3.0
    assert first.track_changed is True
    assert first.planned_departure == datetime.fromisoformat("2026-07-31T09:30:00+0200")


def test_cancelled_departure_without_actual_time():
    second = parse_departures(PAYLOAD)[1]

    assert second.cancelled is True
    assert second.actual_departure is None
    assert second.delay_minutes == 0.0
    assert second.track_changed is False


def test_empty_payload():
    assert parse_departures({"payload": {"departures": []}}) == []