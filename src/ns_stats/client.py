import httpx

BASE_URL = "https://gateway.apiportal.ns.nl/reisinformatie-api/api/v2"

def get_departures(station_code: str, api_key: str) -> dict:
    response = httpx.get(
        f"{BASE_URL}/departures",
        params={"station": station_code},
        headers={"Ocp-Apim-Subscription-Key": api_key},
    )
    response.raise_for_status()
    return response.json()