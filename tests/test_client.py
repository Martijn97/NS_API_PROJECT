import httpx
import respx

from ns_stats.client import get_departures


@respx.mock
def test_get_departures():
    route = respx.get("https://gateway.apiportal.ns.nl/reisinformatie-api/api/v2/departures").mock(
        return_value=httpx.Response(200, json={"payload": {"departures": []}})
    )
    result = get_departures("UT", api_key="dummy")
    assert route.called
    assert "payload" in result