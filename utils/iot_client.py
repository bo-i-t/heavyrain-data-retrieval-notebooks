import os
import requests
from typing import Dict, Any, List, Optional

def api_base() -> str:
    return os.getenv("IOT_API_BASE", "http://localhost:8030").rstrip("/")

def iot_url() -> str:
    return f"{api_base()}/iot"

def _auth_headers() -> dict:
    token = os.getenv("IOT_API_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}

def fetch_iot(
    *,
    dev_eui: Optional[str] = None,
    city: Optional[str] = None,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    hours: int = 168,
    only_with_known_location: bool = True,
    source: str = "auto",
    order: str = "desc",
    limit: int = 1000,
    offset: int = 0,
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    params = {
        "hours": hours,
        "only_with_known_location": str(only_with_known_location).lower(),
        "source": source,
        "order": order,
        "limit": limit,
        "offset": offset,
    }
    if dev_eui: params["dev_eui"] = dev_eui
    if city: params["city"] = city
    if from_ts: params["from_ts"] = from_ts
    if to_ts: params["to_ts"] = to_ts

    r = requests.get(iot_url(), params=params, headers=_auth_headers(), timeout=timeout)
    r.raise_for_status()
    return r.json()

def gauges_url() -> str:
    """
    Base URL for the /gauges endpoint.
    Example: http://localhost:8030/gauges
             or http://localhost:8030/heavyrain/data-api/api/gauges
    depending on IOT_API_BASE.
    """
    return f"{api_base()}/gauges"


def fetch_gauges(
    *,
    city: Optional[str] = None,
    station_name: Optional[str] = None,
    channel: Optional[str] = None,      # "DWD", "LANUK", "WNH"
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    hours: int = 168,
    only_with_known_location: bool = True,
    order: str = "desc",
    limit: int = 1000,
    offset: int = 0,
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    """
    Call the /gauges endpoint and return a list of dicts (JSON rows).

    Parameters mirror the FastAPI /gauges query model (GaugeQuery).
    """
    params: Dict[str, Any] = {
        "hours": hours,
        "only_with_known_location": str(only_with_known_location).lower(),
        "order": order,
        "limit": limit,
        "offset": offset,
    }

    if city:
        params["city"] = city
    if station_name:
        params["station_name"] = station_name
    if channel:            # "DWD", "LANUK", "WNH"
        params["channel"] = channel
    if from_ts:
        params["from_ts"] = from_ts
    if to_ts:
        params["to_ts"] = to_ts

    r = requests.get(
        gauges_url(),
        params=params,
        headers=_auth_headers(),
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()
