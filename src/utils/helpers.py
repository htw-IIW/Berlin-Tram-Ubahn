# src/utils/helpers.py
"""
Parsing and enrichment helpers for raw BVG API responses.
"""

from datetime import datetime, timezone


def _parse_dt(raw: str | None) -> str | None:
    """Return ISO-8601 string or None."""
    if not raw:
        return None
    # BVG API returns RFC 3339 strings — pass through unchanged.
    return raw


def enrich_departure(dep: dict) -> dict:
    """
    Convert one raw BVG API departure object to an Elasticsearch document.
    Adds derived fields (hour_of_day, day_of_week, is_weekend).
    """
    stop      = dep.get("stop") or {}
    line      = dep.get("line") or {}
    location  = stop.get("location") or {}

    planned_when = dep.get("plannedWhen")
    collected_at = datetime.now(timezone.utc).isoformat()

    # Derive hour / weekday from plannedWhen (fall back to now)
    try:
        dt = datetime.fromisoformat(planned_when)
    except (TypeError, ValueError):
        dt = datetime.now(timezone.utc)

    hour_of_day  = dt.hour
    day_of_week  = dt.weekday()   # 0=Mon … 6=Sun
    is_weekend   = day_of_week >= 5

    geo = None
    if location.get("latitude") and location.get("longitude"):
        geo = {"lat": location["latitude"], "lon": location["longitude"]}

    return {
        "collected_at":  collected_at,
        "planned_when":  _parse_dt(planned_when),
        "when":          _parse_dt(dep.get("when")),
        "delay_s":       dep.get("delay"),        # seconds, None if unknown
        "cancelled":     bool(dep.get("cancelled")),
        "line_name":     line.get("name"),
        "line_id":       line.get("id"),
        "direction":     dep.get("direction"),
        "stop_id":       stop.get("id"),
        "stop_name":     stop.get("name"),
        "stop_location": geo,
        "trip_id":       dep.get("tripId"),
        "hour_of_day":   hour_of_day,
        "day_of_week":   day_of_week,
        "is_weekend":    is_weekend,
    }


def enrich_remark(remark: dict, dep: dict) -> dict:
    """
    Convert one BVG API remark (warning/status) to an Elasticsearch disruption document.
    dep is the parent departure, used to attach line/stop context.
    """
    stop = dep.get("stop") or {}
    line = dep.get("line") or {}

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "trip_id":      dep.get("tripId"),
        "line_name":    line.get("name"),
        "direction":    dep.get("direction"),
        "stop_id":      stop.get("id"),
        "stop_name":    stop.get("name"),
        "remark_type":  remark.get("type"),
        "remark_code":  remark.get("code"),
        "summary":      remark.get("summary"),
        "text":         remark.get("text"),
        "valid_from":   _parse_dt(remark.get("validFrom")),
        "valid_until":  _parse_dt(remark.get("validUntil")),
    }
