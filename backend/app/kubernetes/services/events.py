from __future__ import annotations

from typing import Any


def map_event_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert Kubernetes event items into API response dictionaries.
    """

    events: list[dict[str, Any]] = []

    for item in items:
        metadata = item.get("metadata") or {}
        series = item.get("series") or {}
        first_timestamp = (
            item.get("firstTimestamp")
            or item.get("eventTime")
            or metadata.get("creationTimestamp")
            or ""
        )
        last_timestamp = (
            item.get("lastTimestamp")
            or series.get("lastObservedTime")
            or item.get("eventTime")
            or metadata.get("creationTimestamp")
            or ""
        )

        events.append(
            {
                "involved_object": item.get("involvedObject") or item.get("regarding") or {},
                "type": item.get("type") or "",
                "reason": item.get("reason") or "",
                "message": item.get("message") or item.get("note") or "",
                "count": item.get("count") or series.get("count") or 1,
                "first_timestamp": first_timestamp,
                "last_timestamp": last_timestamp,
            }
        )

    return events
