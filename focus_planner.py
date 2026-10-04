"""Focus planner — places study sessions for upcoming assignments.

Reads:
    ~/Documents/ORBIT/dated_events.json       (assignments + their due dates)
    ~/Documents/ORBIT/assignment_estimates.json (hours per assignment)
    ~/Documents/ORBIT/schedule.json           (weekly template, for busy slots)

Writes:
    Focus sessions merged into dated_events.json
"""

import os
import json
import uuid
from datetime import datetime, timedelta


ORBIT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ORBIT")
DATED_EVENTS_PATH = os.path.join(ORBIT_DIR, "dated_events.json")
ESTIMATES_PATH = os.path.join(ORBIT_DIR, "assignment_estimates.json")
SCHEDULE_PATH = os.path.join(ORBIT_DIR, "schedule.json")

# Scheduling window
DAY_START = 7             # earliest hour a session can start
DAY_END   = 23            # latest hour (exclusive)

# Preferred time ranges, in order of preference.
PREFERRED_WINDOWS = [
    (14, 22),   # afternoon / evening
    (9, 12),    # late morning
    (7, 9),     # early morning
    (12, 14),   # midday
]

MAX_HOURS_PER_DAY = 4     # cap per day across all assignments
SLOT_MINUTES      = 30    # scheduling granularity
MAX_HOURS_PER_ASSIGNMENT = 20  # cap to avoid runaway


def plan_focus_sessions():
    """Main entry point. Rewrites dated_events.json in place."""
    events_payload = _load_json(DATED_EVENTS_PATH, {"events": []})
    estimates      = _load_json(ESTIMATES_PATH, {})
    schedule_data  = _load_json(SCHEDULE_PATH, {})

    events = events_payload.get("events", []) or []
    today = datetime.now().date()

    assignments = [e for e in events if e.get("calendar") == "Assignments"]
    existing    = [e for e in events
                   if e.get("calendar") != "Assignments"
                   and e.get("source") != "auto_focus"]

    # Build the free-slot ledger and mark everything that's already busy
    ledger = _build_ledger(today, days=60)
    _mark_template_busy(ledger, schedule_data, today, days=60)
    _mark_busy_from_events(ledger, existing)

    # Rank pending assignments
    pending = _rank_assignments(assignments, estimates, today)

    # Allocate one assignment at a time; each placement reserves slots
    focus_sessions = []
    for p in pending:
        focus_sessions.extend(_allocate_for_assignment(p, ledger, today))

    # Write back
    new_events = existing + assignments + focus_sessions
    new_events.sort(key=lambda e: (e["date"], e["time"]))

    events_payload["events"] = new_events
    events_payload["focus_planned"] = datetime.now().isoformat()

    with open(DATED_EVENTS_PATH, "w") as f:
        json.dump(events_payload, f, indent=2)

    return len(focus_sessions)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------
def _rank_assignments(assignments, estimates, today):
    """Return a sorted list of pending assignments with metadata."""
    pending = []
    for a in assignments:
        if not a.get("all_day"):
            continue

        uuid_str = (a.get("id") or "").replace("asg-", "", 1)
        est = None
        for k, v in estimates.items():
            if k.startswith(uuid_str + ":"):
                est = v
                break
        if not est or not est.get("total_hours"):
            continue

        try:
            due = datetime.strptime(a["date"], "%Y-%m-%d").date()
        except Exception:
            continue
        if due <= today:
            continue  # too late to plan

        try:
            weight = float(a.get("weightage") or 0)
        except (TypeError, ValueError):
            weight = 0

        days_left = (due - today).days
        urgency = max(0.2, 1.0 / max(1, days_left))
        weight_score = max(0.3, min(1.0, weight / 100.0))
        score = urgency * weight_score

        pending.append({
            "event": a,
            "estimate": est,
            "due": due,
            "score": score,
            "days_left": days_left,
        })

    pending.sort(key=lambda x: -x["score"])
    return pending


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------
def _allocate_for_assignment(p, ledger, today):
    """Place sessions for one assignment. Mutates ledger; returns events."""
    event = p["event"]
    est = p["estimate"]
    due = p["due"]

    total_hours = float(est.get("total_hours") or 0)
    if total_hours <= 0:
        return []

    try:
        block_min = int(est.get("session_length_minutes") or 60)
    except (TypeError, ValueError):
        block_min = 60
    block_min = max(30, min(180, block_min))

    total_minutes = min(int(total_hours * 60),
                         MAX_HOURS_PER_ASSIGNMENT * 60)

    # Window: [today, due - 1], or [today] if due is tomorrow
    window_start = today
    window_end = due - timedelta(days=1)
    if window_end < window_start:
        window_end = today
    days_in_window = (window_end - window_start).days + 1
    if days_in_window <= 0:
        return []

    # Back-loaded distribution: later days get more minutes
    total_weight = sum(i + 1 for i in range(days_in_window))
    day_budgets = [int(total_minutes * (i + 1) / total_weight)
                   for i in range(days_in_window)]
    diff = total_minutes - sum(day_budgets)
    if day_budgets:
        day_budgets[-1] += diff

    verb = _verb_for_estimate(est)
    base = event.get("activity", "Assignment")
    activity = f"{verb}: {base[:40]}"

    sessions = []
    for i in range(days_in_window):
        d = window_start + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        remaining_today = min(day_budgets[i], MAX_HOURS_PER_DAY * 60)
        if remaining_today < 30:
            continue

        for (win_start, win_end) in PREFERRED_WINDOWS:
            if remaining_today < 30:
                break
            runs = _find_free_slots(ledger, d_str, win_start, win_end)
            for (run_start, run_len) in runs:
                if remaining_today < 30:
                    break
                cursor = run_start
                run_end = run_start + run_len
                while remaining_today >= 30 and cursor < run_end:
                    available = (run_end - cursor) * SLOT_MINUTES
                    this_block = min(block_min, remaining_today, available)
                    this_block = (this_block // SLOT_MINUTES) * SLOT_MINUTES
                    if this_block < 30:
                        break

                    start_hour = DAY_START + (cursor * SLOT_MINUTES) // 60
                    start_minute = (cursor * SLOT_MINUTES) % 60

                    _reserve_slots(ledger, d_str, start_hour, start_minute,
                                   this_block)

                    sessions.append(_make_session(
                        date_str=d_str,
                        hour=start_hour,
                        minute=start_minute,
                        duration_min=this_block,
                        activity=activity,
                        assignment=event,
                    ))
                    cursor += this_block // SLOT_MINUTES
                    remaining_today -= this_block

    return sessions


def _make_session(date_str, hour, minute, duration_min, activity, assignment):
    return {
        "id": f"focus-{uuid.uuid4().hex[:8]}",
        "date": date_str,
        "time": _format_time(hour, minute),
        "end_time": _format_time_from_minutes(hour, minute, duration_min),
        "activity": activity,
        "course": assignment.get("course", ""),
        "course_code": assignment.get("course_code", ""),
        "calendar": "Study",
        "source": "auto_focus",
        "duration_min": duration_min,
        "all_day": False,
        "parent_assignment_id": assignment.get("id", ""),
    }


def _verb_for_estimate(est):
    t = (est.get("type") or "").lower()
    return {
        "doing":    "Build",
        "writing":  "Write",
        "research": "Research",
        "admin":    "Do",
    }.get(t, "Work on")


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
def _build_ledger(start_date, days=60):
    ledger = {}
    slots_per_day = (DAY_END - DAY_START) * (60 // SLOT_MINUTES)
    for i in range(days):
        d_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for s in range(slots_per_day):
            ledger[(d_str, s)] = True
    return ledger


def _mark_template_busy(ledger, schedule_data, today, days=60):
    weekly = (schedule_data or {}).get("schedule") or {}
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                     'Friday', 'Saturday', 'Sunday']
    for i in range(days):
        d = today + timedelta(days=i)
        wd_name = weekday_names[d.weekday()]
        d_str = d.strftime("%Y-%m-%d")
        for ev in weekly.get(wd_name, []) or []:
            if ev.get("all_day"):
                continue
            try:
                hh, mm = _parse_hhmm(ev.get("time", ""))
            except Exception:
                continue
            _reserve_slots(ledger, d_str, hh, mm, _duration_minutes(ev))


def _mark_busy_from_events(ledger, events):
    for ev in events:
        if ev.get("all_day"):
            continue
        d_str = ev.get("date", "")
        if not d_str:
            continue
        try:
            hh, mm = _parse_hhmm(ev.get("time", ""))
        except Exception:
            continue
        _reserve_slots(ledger, d_str, hh, mm, _duration_minutes(ev))


def _reserve_slots(ledger, date_str, start_hour, start_minute, duration_min):
    if duration_min <= 0:
        duration_min = 60
    start_slot = ((start_hour - DAY_START) * (60 // SLOT_MINUTES)
                  + (start_minute // SLOT_MINUTES))
    num_slots = max(1, (duration_min + SLOT_MINUTES - 1) // SLOT_MINUTES)
    for i in range(num_slots):
        key = (date_str, start_slot + i)
        if key in ledger:
            ledger[key] = False


def _find_free_slots(ledger, date_str, start_hour, end_hour):
    slots_per_day = (DAY_END - DAY_START) * (60 // SLOT_MINUTES)
    s0 = max(0, (start_hour - DAY_START) * (60 // SLOT_MINUTES))
    s1 = min(slots_per_day, (end_hour - DAY_START) * (60 // SLOT_MINUTES))

    runs = []
    current = []
    for s in range(s0, s1):
        if ledger.get((date_str, s), False):
            current.append(s)
        else:
            if current:
                runs.append((current[0], len(current)))
                current = []
    if current:
        runs.append((current[0], len(current)))
    return runs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default


def _parse_hhmm(t):
    dt = datetime.strptime(t.strip().upper(), "%I:%M %p")
    return dt.hour, dt.minute


def _duration_minutes(ev):
    if ev.get("duration_min"):
        try:
            return int(ev["duration_min"])
        except (TypeError, ValueError):
            pass
    end = ev.get("end_time", "")
    start = ev.get("time", "")
    if end and start:
        try:
            sh, sm = _parse_hhmm(start)
            eh, em = _parse_hhmm(end)
            return max(30, (eh * 60 + em) - (sh * 60 + sm))
        except Exception:
            pass
    return 60


def _format_time(hour, minute):
    if hour == 0:  return f"12:{minute:02d} AM"
    if hour < 12:  return f"{hour}:{minute:02d} AM"
    if hour == 12: return f"12:{minute:02d} PM"
    return f"{hour-12}:{minute:02d} PM"


def _format_time_from_minutes(hour, minute, duration_min):
    total = hour * 60 + minute + duration_min
    h = (total // 60) % 24
    m = total % 60
    return _format_time(h, m)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    n = plan_focus_sessions()
    print(f"Placed {n} focus sessions.")
    print(f"Updated: {DATED_EVENTS_PATH}")