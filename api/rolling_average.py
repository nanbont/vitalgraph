"""Rolling average in Python — MySQL only supports row-count windows, not time-based ones."""

from datetime import datetime, timedelta
from statistics import mean


def with_rolling_average(
    readings: list[dict],
    value_key: str,
    window_minutes: int = 10,
) -> list[dict]:
    """
    readings: list of dicts with 'recorded_at' (datetime) and value_key,
              expected sorted DESCENDING (newest first) as MySQL returns them.
    Returns the same list (still newest first), each dict annotated with
    'rolling_avg'.
    """
    if not readings:
        return []

    # Work ascending internally so the "preceding window" logic reads naturally,
    # then reverse back before returning.
    ascending = list(reversed(readings))
    window = timedelta(minutes=window_minutes)
    result = []

    for i, r in enumerate(ascending):
        recorded_at = r["recorded_at"]
        if isinstance(recorded_at, str):
            recorded_at = datetime.fromisoformat(recorded_at)
        cutoff = recorded_at - window

        in_window = []
        for x in ascending[: i + 1]:
            x_time = x["recorded_at"]
            if isinstance(x_time, str):
                x_time = datetime.fromisoformat(x_time)
            if x_time >= cutoff:
                in_window.append(x[value_key])

        annotated = dict(r)
        annotated["rolling_avg"] = round(mean(in_window), 1) if in_window else None
        result.append(annotated)

    return list(reversed(result))
