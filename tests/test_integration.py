import os

import pytest

from ns_api_project.client import get_departures
from ns_api_project.transform import parse_departures


@pytest.mark.integration
def test_live_response_matches_transform_contract():
    payload = get_departures("UT", api_key=os.environ["NS_API_KEY"])
    departures = parse_departures(payload)

    assert departures, "expected at least one departure from Utrecht Centraal"

    first = departures[0]
    assert first.destination
    assert first.train_category
    assert first.planned_departure is not None
    assert first.delay_minutes >= 0 or first.cancelled