"""Orchestrator — the single entry point the app uses to fetch external data.

Connectors currently wired in:
  - CoachLMSConnector  → sessions (classes) + assignments (deadlines)
  - GmailConnector     → calendar invites from email (.ics attachments)
"""

import json
import os
from datetime import datetime

from connectors.coach_lms import CoachLMSConnector
from connectors.gmail import GmailConnector


ORBIT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ORBIT")
DATED_EVENTS_PATH = os.path.join(ORBIT_DIR, "dated_events.json")


class Orchestrator:
    def __init__(self):
        self.connectors = []
        self.gmail = None

        try:
            self.connectors.append(CoachLMSConnector())
        except Exception as e:
            print(f"[orchestrator] Coach LMS connector unavailable: {e}")

        try:
            self.gmail = GmailConnector()
        except Exception as e:
            print(f"[orchestrator] Gmail connector unavailable: {e}")

    # ------------------------------------------------------------------
    def fetch_all(self, days_ahead=30):
        """Call every connector and merge the results.

        Returns:
            {
              'events': [ ... dated event dicts ... ],
              'sources': {'CoachLMSConnector.sessions': 23, ...},
              'errors':  ['...']
            }
        """
        merged = []
        sources = {}
        errors = []

        for conn in self.connectors:
            name = conn.__class__.__name__

            # --- Sessions (dated classes) ---
            try:
                brief = conn.fetch_week(days=days_ahead)
                classes = brief.get("classes", []) or []
                for c in classes:
                    merged.append(_to_dated_event(c))
                sources[f"{name}.sessions"] = len(classes)
            except Exception as e:
                errors.append(f"{name}.sessions: {e}")

            # --- Assignments (deadlines) ---
            try:
                assignments = conn.fetch_assignments(days_ahead=days_ahead * 2)
                kept = 0
                for a in assignments:
                    if a.get("submitted"):
                        continue
                    merged.append(_to_assignment_event(a))
                    kept += 1
                sources[f"{name}.assignments"] = kept
            except Exception as e:
                errors.append(f"{name}.assignments: {e}")

        # --- Gmail invites ---
        if self.gmail:
            try:
                window = max(days_ahead, 30)
                result = self.gmail.fetch_recent(days_back=window)
                invites = result.get("invites", []) or []

                today = datetime.now().date()
                kept = 0
                for inv in invites:
                    start_iso = inv.get("start", "")
                    if not start_iso:
                        continue
                    try:
                        start_dt = datetime.fromisoformat(start_iso)
                    except Exception:
                        continue
                    if start_dt.date() < today:
                        continue
                    merged.append(_to_invite_event(inv))
                    kept += 1
                sources["GmailConnector.invites"] = kept
            except Exception as e:
                errors.append(f"GmailConnector.invites: {e}")

        merged.sort(key=lambda e: (e["date"], e["time"]))

        return {
            "events": merged,
            "sources": sources,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    def refresh(self, days_ahead=30):
        """Fetch everything and write to dated_events.json."""
        result = self.fetch_all(days_ahead=days_ahead)

        os.makedirs(ORBIT_DIR, exist_ok=True)
        payload = {
            "version": 1,
            "updated": datetime.now().isoformat(),
            "sources": result["sources"],
            "errors": result["errors"],
            "events": result["events"],
        }
        with open(DATED_EVENTS_PATH, "w") as f:
            json.dump(payload, f, indent=2)

        return payload


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------
def _to_dated_event(c):
    """Convert a Coach LMS session into a dated event."""
    return {
        "id":           f"lms-{c.get('course_code', 'x')}-{c['date']}-{c['start']}",
        "date":         c["date"],
        "time":         _to_12h(c["start"]),
        "end_time":     _to_12h(c["end"]),
        "activity":     c["name"],
        "course":       c.get("course", ""),
        "course_code":  c.get("course_code", ""),
        "calendar":     "Classes",
        "meeting_link": c.get("meeting_link", ""),
        "source":       "coach_lms",
        "all_day":      False,
    }


def _to_assignment_event(a):
    """Convert an assignment into an all-day dated event."""
    return {
        "id":          f"asg-{a.get('uuid', 'x')}",
        "date":        a["due"],
        "time":        "All day",
        "end_time":    "",
        "activity":    a["name"],
        "course":      a.get("course", ""),
        "course_code": a.get("course_code", ""),
        "calendar":    "Assignments",
        "weightage":   a.get("weightage", ""),
        "is_group":    a.get("is_group", False),
        "source":      "coach_lms",
        "all_day":     True,
    }


def _to_invite_event(inv):
    """Convert a Gmail calendar invite into a dated event."""
    start_iso = inv.get("start", "")
    end_iso = inv.get("end", "") or ""

    try:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso) if end_iso else None
    except Exception:
        start_dt = None
        end_dt = None

    date_str = start_dt.strftime("%Y-%m-%d") if start_dt else ""
    start_h = _to_12h_from_dt(start_dt)
    end_h = _to_12h_from_dt(end_dt) if end_dt else ""

    return {
        "id":          f"inv-{inv.get('uid', 'x')}",
        "date":        date_str,
        "time":        start_h,
        "end_time":    end_h,
        "activity":    inv.get("summary", "Meeting"),
        "location":    inv.get("location", ""),
        "calendar":    "Meetings",
        "source":      "gmail",
        "all_day":     False,
    }


def _to_12h(hhmm):
    """'09:30' -> '9:30 AM'"""
    try:
        h, m = hhmm.split(":")
        h = int(h)
        suffix = "AM" if h < 12 else "PM"
        h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
        return f"{h12}:{m} {suffix}"
    except Exception:
        return hhmm


def _to_12h_from_dt(dt):
    """datetime -> '9:30 AM'"""
    if not dt:
        return ""
    h = dt.hour
    suffix = "AM" if h < 12 else "PM"
    h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
    return f"{h12}:{dt.minute:02d} {suffix}"


# ---------------------------------------------------------------------------
# CLI for testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    orch = Orchestrator()
    payload = orch.refresh(days_ahead=30)

    print(f"Wrote {DATED_EVENTS_PATH}")
    print(f"Sources: {payload['sources']}")
    if payload["errors"]:
        print("Errors:")
        for e in payload["errors"]:
            print(f"  - {e}")

    # Split display
    by_source = {}
    for ev in payload["events"]:
        src = ev.get("source", "?")
        by_source.setdefault(src, []).append(ev)

    for src, events in by_source.items():
        print(f"\n{src}  ({len(events)}):")
        for ev in events[:6]:
            time_part = ev["time"] if ev["time"] != "All day" else "       All day"
            print(f"  {ev['date']}  {time_part:>12s}  "
                  f"{ev['activity'][:50]}")
        if len(events) > 6:
            print(f"  ... and {len(events) - 6} more")