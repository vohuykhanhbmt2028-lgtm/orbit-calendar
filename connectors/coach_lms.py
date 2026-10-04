"""Coach LMS connector — fetches sessions from the Tetr/Masters' Union API."""

import os
from datetime import datetime, timedelta

import requests


BASE_URL = "https://tetr.mastersunion.in/api/v1"
TERM_ID = "73dc510f-a4d2-4b01-adf7-ac9e0cbbc14e"

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]


class CoachLMSConnector:
    def __init__(self):
        self.token = os.getenv("COACH_LMS_TOKEN", "").strip()
        if not self.token:
            raise RuntimeError(
                "COACH_LMS_TOKEN not set in .env file. "
                "Add it or see the setup instructions."
            )

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Origin":  "https://coach.tetr.com",
            "Referer": "https://coach.tetr.com/",
            "Accept":  "application/json, text/plain, */*",
        }

    def fetch_raw(self):
        """Call the API and return the raw JSON."""
        url = f"{BASE_URL}/program/{TERM_ID}/getUpcomingSessionsCourses"
        resp = requests.get(
            url,
            params={"termData": TERM_ID},
            headers=self._headers(),
            timeout=20,
        )

        if resp.status_code == 401:
            raise RuntimeError(
                "Coach LMS rejected the token (401). "
                "It may have been invalidated by logging out. "
                "Re-extract it from DevTools and update .env."
            )
        resp.raise_for_status()
        return resp.json()

    def fetch_week(self, week_start=None, days=7):
        """Return upcoming classes as dated events.

        days=7  -> this week (default)
        days=30 -> next 30 days
        """
        if week_start is None:
            week_start = datetime.now().date()

        week_start = _to_date(week_start)
        week_end = week_start + timedelta(days=days - 1)

        raw = self.fetch_raw()
        classes = []

        for course in raw.get("Data", []):
            master = course.get("CourseMaster", {}) or {}
            course_name = master.get("name", "Untitled course")
            course_code = master.get("courseCode", "")

            for session in course.get("SessionDetails", []) or []:
                session_date = _parse_date(session.get("sessionDate", ""))
                if session_date is None:
                    continue
                if not (week_start <= session_date <= week_end):
                    continue

                classes.append({
                    "name":         session.get("sessionName", "Session"),
                    "course":       course_name,
                    "course_code":  course_code,
                    "date":         session_date.isoformat(),
                    "weekday":      WEEKDAY_NAMES[session_date.weekday()],
                    "start":        session.get("fromTime", ""),
                    "end":          session.get("toTime", ""),
                    "meeting_link": session.get("meetingLink", ""),
                })

        classes.sort(key=lambda c: (c["date"], c["start"]))
        return {"classes": classes, "source": "coach_lms"}

    def fetch_assignments(self, days_ahead=60):
        """Return upcoming assignments as dated events."""
        url = f"{BASE_URL}/program/assignments/term/{TERM_ID}/getAllStudentAssignments"
        params = {
            "sort": "submissionDate",
            "type": "all",
            "search": "",
        }

        resp = requests.get(
            url,
            params=params,
            headers=self._headers(),
            timeout=20,
        )
        if resp.status_code == 401:
            raise RuntimeError(
                "Coach LMS rejected the token (401). "
                "Re-extract it from DevTools and update .env."
            )
        resp.raise_for_status()
        data = resp.json()

        today = datetime.now().date()
        horizon = today + timedelta(days=days_ahead)

        assignments = []
        for a in data.get("data", {}).get("assignment", []) or []:
            iso = a.get("submissionDate")
            if not iso:
                continue
            due = _parse_date(iso)
            if due is None:
                continue
            # Include anything due from now until the horizon
            if not (today <= due <= horizon):
                continue

            course = (a.get("TermCourse", {}) or {}).get("CourseMaster", {}) or {}
            assignments.append({
                "uuid":         a.get("uuid", ""),
                "name":         a.get("name", "Untitled assignment"),
                "course":       course.get("name", ""),
                "course_code":  course.get("courseCode", ""),
                "due":          due.isoformat(),
                "submitted":    bool(a.get("latestSubmissionExists")),
                "weightage":    a.get("weightagePercentage", "") or "",
                "is_group":     bool(a.get("isGroup", False)),
                "details_html": a.get("assignmentDetails", "") or "",
                "total_points": a.get("totalPoints", "") or "",
            })

        assignments.sort(key=lambda x: x["due"])
        return assignments

def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.fromisoformat(value).date()
    return value


def _parse_date(iso):
    """Parse '2026-10-06T00:00:00.000Z' into a date."""
    if not iso:
        return None
    try:
        clean = iso.replace("Z", "+00:00")
        return datetime.fromisoformat(clean).date()
    except Exception:
        return None


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    conn = CoachLMSConnector()
    brief = conn.fetch_week()

    print(f"Source: {brief['source']}")
    print(f"Sessions this week: {len(brief['classes'])}\n")
    for c in brief["classes"]:
        print(f"  {c['weekday']:9s} {c['date']}  "
              f"{c['start']}-{c['end']}  {c['name']}  ({c['course_code']})")
