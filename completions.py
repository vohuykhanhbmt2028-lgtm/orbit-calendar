"""Completion log — records what happened with each event.

Storage:
    ~/Documents/ORBIT/completions.json

Shape:
    {
      "entries": {
        "<event_id>|<date>": {
            "event_id":          "...",
            "date":              "YYYY-MM-DD",
            "activity":          "...",
            "status":            "done" | "skipped" | "partial",
            "planned_minutes":   int or null,
            "actual_minutes":    int or null,
            "logged_at":         ISO datetime,
            "source":            "template" | "auto_focus" | "coach_lms" | "gmail"
        },
        ...
      }
    }
"""

import os
import json
from datetime import datetime


ORBIT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ORBIT")
COMPLETIONS_PATH = os.path.join(ORBIT_DIR, "completions.json")


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------
def _load():
    if not os.path.exists(COMPLETIONS_PATH):
        return {"entries": {}}
    try:
        with open(COMPLETIONS_PATH, "r") as f:
            data = json.load(f)
        data.setdefault("entries", {})
        return data
    except Exception:
        return {"entries": {}}


def _save(data):
    os.makedirs(ORBIT_DIR, exist_ok=True)
    with open(COMPLETIONS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _key(event_id, date_str):
    return f"{event_id}|{date_str}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def all_entries():
    """Return the full entries dict keyed by '<id>|<date>'."""
    return _load()["entries"]


def get(event_id, date_str):
    return _load()["entries"].get(_key(event_id, date_str))


def log(event_id, date_str, activity, status,
        planned_minutes=None, actual_minutes=None, source=None):
    """Record a completion. Overwrites any existing entry for the same key."""
    data = _load()
    key = _key(event_id, date_str)
    data["entries"][key] = {
        "event_id":         event_id,
        "date":             date_str,
        "activity":         activity,
        "status":           status,
        "planned_minutes":  planned_minutes,
        "actual_minutes":   actual_minutes,
        "logged_at":        datetime.now().isoformat(),
        "source":           source or "",
    }
    _save(data)
    return data["entries"][key]


def clear(event_id, date_str):
    """Remove a completion entry."""
    data = _load()
    key = _key(event_id, date_str)
    if key in data["entries"]:
        del data["entries"][key]
        _save(data)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def weekly_summary(week_start):
    """Return counts for the 7 days beginning on week_start (a date)."""
    from datetime import timedelta
    end = week_start + timedelta(days=6)
    entries = _load()["entries"].values()
    done = skipped = partial = 0
    for e in entries:
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if not (week_start <= d <= end):
            continue
        s = e.get("status")
        if s == "done":      done += 1
        elif s == "skipped": skipped += 1
        elif s == "partial": partial += 1
    return {"done": done, "skipped": skipped, "partial": partial}


def lifetime_counts():
    entries = _load()["entries"].values()
    done = skipped = partial = 0
    for e in entries:
        s = e.get("status")
        if s == "done":      done += 1
        elif s == "skipped": skipped += 1
        elif s == "partial": partial += 1
    return {"done": done, "skipped": skipped, "partial": partial}


def personal_multiplier(min_samples=5):
    """Average(actual / planned) across logged entries that have both.

    Returns None if fewer than `min_samples` data points exist.
    """
    ratios = []
    for e in _load()["entries"].values():
        planned = e.get("planned_minutes")
        actual  = e.get("actual_minutes")
        if not planned or not actual:
            continue
        try:
            ratios.append(float(actual) / float(planned))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    if len(ratios) < min_samples:
        return None
    return round(sum(ratios) / len(ratios), 3)