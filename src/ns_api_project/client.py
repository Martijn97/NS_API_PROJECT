"""HTTP access to the NS Reisinformatie API.

This module is the only place that talks to the network. Everything downstream
(`transform`, `aggregate`) works on plain dicts and dataclasses, which is what
makes those modules testable without mocking HTTP.
"""

import httpx

BASE_URL = "https://gateway.apiportal.ns.nl/reisinformatie-api/api/v2"


def get_departures(station_code: str, api_key: str) -> dict:
    """Fetch the raw departures payload for a station.

    Args:
        station_code: NS station abbreviation, e.g. "UT", "ASD", "RTD".
        api_key: NS API subscription key (see README for how to get one).

    Returns:
        The decoded JSON response as-is; parsing happens in `transform`.

    Raises:
        httpx.HTTPStatusError: on any non-2xx response, e.g. 401 for a bad key.
    """
    response = httpx.get(
        f"{BASE_URL}/departures",
        params={"station": station_code},
        # Azure API Management header used by the NS API portal.
        headers={"Ocp-Apim-Subscription-Key": api_key},
    )
    response.raise_for_status()
    return response.json()