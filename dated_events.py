"""Loader and refresher for dated_events.json (produced by the orchestrator)."""

import os
import json
import subprocess
import sys


ORBIT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ORBIT")
DATED_EVENTS_PATH = os.path.join(ORBIT_DIR, "dated_events.json")
ESTIMATES_PATH = os.path.join(ORBIT_DIR, "assignment_estimates.json")


def load_events():
    """Return the list of dated events (empty list if none)."""
    if not os.path.exists(DATED_EVENTS_PATH):
        return []
    try:
        with open(DATED_EVENTS_PATH, "r") as f:
            data = json.load(f)
        return data.get("events", []) or []
    except Exception:
        return []


def load_estimates():
    """Return {uuid: estimate_dict} for all cached estimates."""
    if not os.path.exists(ESTIMATES_PATH):
        return {}
    try:
        with open(ESTIMATES_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def refresh_from_lms():
    """Run the orchestrator as a subprocess. Returns (ok, message)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        result = subprocess.run(
            [sys.executable, "-m", "connectors.orchestrator"],
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "unknown error").strip()
            return False, err.splitlines()[-1] if err else "Failed"
        # Return a summary line if the orchestrator printed one
        try:
            import focus_planner
            n = focus_planner.plan_focus_sessions()
            focus_note = f" · {n} focus sessions planned"
        except Exception as e:
            focus_note = f" · focus planner failed: {e}"

        for line in (result.stdout or "").splitlines():
            if line.startswith("Sources:"):
                return True, line + focus_note
        return True, "Refreshed" + focus_note
    except subprocess.TimeoutExpired:
        return False, "Refresh timed out (over 3 min)"
    except Exception as e:
        return False, str(e)