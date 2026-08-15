"""Time helpers that keep persisted MongoDB dates consistently in UTC."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC time in PyMongo's default naive-UTC form.

    Existing MongoDB records are decoded as naive UTC datetimes. Keeping newly
    created values in that form prevents invalid aware/naive comparisons while
    avoiding the deprecated ``datetime.utcnow()`` API.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
