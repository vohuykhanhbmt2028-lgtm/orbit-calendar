"""Assignment estimator — decomposition-based estimation with filtering.

Claude enumerates deliverables. We filter out optional items, admin
overhead, and inflated coordination before summing. The total is what
remains — real, focused work.
"""

import os
import re
import json
import hashlib
import html
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv()

ORBIT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ORBIT")
ESTIMATES_PATH = os.path.join(ORBIT_DIR, "assignment_estimates.json")

MODEL = "claude-haiku-4-5-20251001"

# Final safety multiplier applied after filtering. Keep at 1.0 unless
# everything still drifts high.
SCALE_FACTOR = 1.0

# Maximum coordination allowance for a group assignment, in minutes.
COORD_CAP_NORMAL = 90
COORD_CAP_BIG = 180    # for capstones / projects > 15h

# Max minutes any single deliverable can consume.
DELIVERABLE_CAP = 300


# ---------------------------------------------------------------------------
# Filtering rules
# ---------------------------------------------------------------------------
# Deliverables whose names match these patterns get dropped entirely.
DROP_PATTERNS = [
    r"\bread\b.*\bbrief\b",
    r"\breading\b.*\bbrief\b",
    r"\breview\b.*\brequirements\b",
    r"\bunderstand\b.*\brequirements\b",
    r"\bcover page\b",
    r"\bai declaration\b",
    r"\bmetadata\b",
    r"\bproofread",
    r"\bformatting\b",
    r"\bpdf submission\b",
    r"\bsubmission prep\b",
    r"\baccount setup\b",
    r"\bplatform familiarization\b",
    r"\binitial setup\b",
    r"\btechnology setup\b",
]

# Deliverables whose names match these get dropped IF they also contain
# one of the optional markers.
OPTIONAL_MARKERS = [
    r"\boptional\b",
    r"\bif attempted\b",
    r"\bif conducted\b",
    r"\bif pursued\b",
    r"\bbonus\b",
    r"\bif time allows\b",
]


def _is_droppable(name):
    n = name.lower()
    for pat in DROP_PATTERNS:
        if re.search(pat, n):
            return True
    return False


def _is_optional(name):
    n = name.lower()
    for pat in OPTIONAL_MARKERS:
        if re.search(pat, n):
            return True
    return False


# ---------------------------------------------------------------------------
# Anchors
# ---------------------------------------------------------------------------
REFERENCE_POINTS = """\
Realistic effort per deliverable, for a competent student working
efficiently. These are what the work ACTUALLY takes — not what a
perfectionist would spend.

WRITING (assume 500–800 words per focused hour):
  - Short reflection (~300 words):              20–30 min
  - Discussion post (~300 words):               15–20 min
  - Reflection (~500 words):                    30–45 min
  - Essay (~1,000 words, light research):       90–120 min
  - Essay (~2,500 words, light research):       4–6 hours
  - Essay (~2,500 words, heavy research):       8–12 hours
  - Case write-up (2,500 words + analysis):     4–6 hours
  - Report with calculations + tables:          3–6 hours
  - Any single section of a report:             scale by word count at
                                                600 words/hour

DOING (build / code / model / simulate):
  - Excel + Solver modeling:                    2–4 hours
  - Small programming task:                     1–2 hours
  - Medium programming assignment:              4–8 hours
  - Data cleaning (medium dataset):             1–2 hours
  - ML model build + evaluation:                3–5 hours
  - Full data science project (clean → model → report):  10–15 hours
  - Figma mockup (basic clickable):             2–3 hours
  - High-fidelity interactive prototype:        4–6 hours
  - Live portfolio simulation (ongoing mgmt):   6–10 hours spread over weeks
  - Capstone / multi-phase build:               12–20 hours

READING & ANALYSIS:
  - HBS-style case (read + notes):              45–60 min
  - Academic paper read + summary:              30–45 min
  - Dataset exploration / EDA:                  60–90 min

RESEARCH:
  - Scheduling + conducting 1 interview:        45–75 min
  - 2+ interviews (scheduling + notes):         90–120 min
  - Running a small survey (5+ responses):      90–150 min
  - Competitor / pricing audit:                 90–120 min

ADMIN:
  - Feedback form / survey:                     5 min
  - Single-question poll:                       2 min

GROUP COORDINATION (added by the code, not by you):
  Coordination is handled by the calling code, NOT included here.
"""


SYSTEM_PROMPT = f"""\
You are an experienced academic coach. For the assignment brief below,
enumerate every REQUIRED concrete deliverable, estimate each in minutes,
and return the breakdown as JSON.

{REFERENCE_POINTS}

METHOD
======
1. Read the brief. Identify each REQUIRED thing the student must
   produce — each section, each file, each analysis, each model.
2. SKIP entirely: reading the brief, account setup, tool setup,
   proofreading, formatting, cover pages, AI declarations, submission
   prep, and any item marked "optional", "bonus", or "if attempted".
3. For each remaining deliverable, pick the closest anchor above and
   give a realistic MINUTES estimate.
4. Do NOT inflate. Do NOT round up to be safe. A 500-word reflection is
   30–45 minutes. A Figma mockup is 2–4 hours, not 6.

OUTPUT — strict JSON, no code fences, no surrounding text:

{{
  "type": "admin" | "writing" | "doing" | "research" | "mixed",
  "deliverables": [
    {{"name": "<short, concrete>", "kind": "writing|doing|reading|research|admin", "minutes": <int>}},
    ...
  ],
  "confidence": "high" | "medium" | "low",
  "reasoning": "<one sentence explaining the main driver of the estimate>",
  "session_length_minutes": <30 | 45 | 60 | 90 | 120>,
  "intensity": "shallow" | "medium" | "deep",
  "notes": "<one short line of practical advice, optional>"
}}

Rules:
- 2–6 deliverables. Fewer for small assignments.
- If the type is "admin", output exactly ONE deliverable of ≤10 minutes.
- Do NOT include a coordination deliverable — the code adds it.
- session_length_minutes: 60 for shallow/reading, 90 for writing/research,
  120 for coding/building, 30 for admin.
"""


class AssignmentEstimator:
    def __init__(self):
        key = os.getenv("CLAUDE_API_KEY")
        if not key:
            raise RuntimeError("CLAUDE_API_KEY not set in .env")
        self.client = Anthropic(api_key=key)
        self.cache = self._load_cache()

    # ------------------------------------------------------------------
    def _load_cache(self):
        if not os.path.exists(ESTIMATES_PATH):
            return {}
        try:
            with open(ESTIMATES_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self):
        os.makedirs(ORBIT_DIR, exist_ok=True)
        with open(ESTIMATES_PATH, "w") as f:
            json.dump(self.cache, f, indent=2)

    @staticmethod
    def _cache_key(uuid, description):
        h = hashlib.sha1((description or "").encode("utf-8")).hexdigest()[:12]
        return f"{uuid}:{h}"

    # ------------------------------------------------------------------
    def estimate_all(self, assignments, force=False):
        results = {}
        for a in assignments:
            uuid = a.get("uuid", "")
            if not uuid:
                continue
            results[uuid] = self.estimate_one(a, force=force)
        self._save_cache()
        return results

    def estimate_one(self, assignment, force=False):
        uuid = assignment.get("uuid", "")
        details = assignment.get("details_html", "") or ""
        key = self._cache_key(uuid, details)
        if not force and key in self.cache:
            return self.cache[key]
        estimate = self._call_claude(assignment)
        self.cache[key] = estimate
        return estimate

    # ------------------------------------------------------------------
    def _call_claude(self, assignment):
        name = assignment.get("name", "Untitled assignment")
        course = assignment.get("course", "")
        course_code = assignment.get("course_code", "")
        due = assignment.get("due", "")
        weight = assignment.get("weightage", "")
        is_group = assignment.get("is_group", False)
        details = _clean_html(assignment.get("details_html", ""))

        if len(details) > 4000:
            details = details[:4000] + " … [truncated]"

        meta_lines = [
            f"Name: {name}",
            f"Course: {course} ({course_code})" if course_code else f"Course: {course}",
            f"Due: {due}",
        ]
        if weight:
            meta_lines.append(f"Weightage: {weight}% of course grade")
        if is_group:
            meta_lines.append("This is a GROUP assignment.")
        else:
            meta_lines.append("This is an INDIVIDUAL assignment.")

        user_message = (
            "\n".join(meta_lines)
            + "\n\n--- Assignment brief ---\n"
            + details
        )

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=900,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            raw = response.content[0].text.strip()
            parsed = self._parse_response(raw)
            return self._finalize(parsed, is_group)
        except Exception as e:
            return {
                "type": "unknown",
                "deliverables": [],
                "total_hours": None,
                "confidence": "low",
                "reasoning": f"Estimation failed: {e}",
                "session_length_minutes": 60,
                "session_count": 0,
                "intensity": "medium",
                "notes": "",
                "error": True,
            }

    # ------------------------------------------------------------------
    def _finalize(self, data, is_group):
        """Filter, cap, add coordination, sum."""
        raw = data.get("deliverables") or []

        # 1. Filter
        kept = []
        for d in raw:
            name = d.get("name", "") or ""
            if _is_droppable(name):
                continue
            if _is_optional(name):
                continue
            try:
                minutes = int(d.get("minutes", 0))
            except (TypeError, ValueError):
                continue
            if minutes <= 0:
                continue
            minutes = min(minutes, DELIVERABLE_CAP)
            kept.append({
                "name": name,
                "kind": d.get("kind", "doing"),
                "minutes": minutes,
            })

        # 2. Hard cap for admin
        if data.get("type") == "admin":
            kept = [{"name": "Complete form", "kind": "admin", "minutes": 5}]

        # 3. Add coordination for group assignments
        if is_group:
            subtotal = sum(d["minutes"] for d in kept)
            coord_min = COORD_CAP_BIG if subtotal >= 15 * 60 else COORD_CAP_NORMAL
            kept.append({
                "name": "Group coordination (meetings + merge)",
                "kind": "coordination",
                "minutes": coord_min,
            })

        # 4. Sum
        total_minutes = sum(d["minutes"] for d in kept)
        total_hours = round(total_minutes / 60.0, 2)
        if SCALE_FACTOR != 1.0:
            total_hours = round(total_hours * SCALE_FACTOR, 2)
            total_minutes = int(total_hours * 60)

        data["deliverables"] = kept
        data["total_hours"] = total_hours
        data["total_minutes"] = total_minutes

        block = data.get("session_length_minutes") or 60
        data["session_count"] = (
            int(-(-total_hours * 60 // block)) if total_hours > 0 and block > 0 else 0
        )
        return data

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_response(raw):
        if raw.startswith("```"):
            first_nl = raw.find("\n")
            if first_nl != -1:
                raw = raw[first_nl + 1:]
            if raw.rstrip().endswith("```"):
                raw = raw.rstrip()[:-3]
            raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw)
            if not m:
                raise
            data = json.loads(m.group())

        data.setdefault("type", "unknown")
        data.setdefault("deliverables", [])
        data.setdefault("confidence", "medium")
        data.setdefault("reasoning", "")
        data.setdefault("session_length_minutes", 60)
        data.setdefault("intensity", "medium")
        data.setdefault("notes", "")
        return data


# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean_html(html_text):
    if not html_text:
        return ""
    text = _TAG_RE.sub(" ", html_text)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    return text


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from connectors.coach_lms import CoachLMSConnector

    force = "--force" in sys.argv

    print("Fetching assignments from Coach LMS...")
    conn = CoachLMSConnector()
    assignments = conn.fetch_assignments(days_ahead=60)
    pending = [a for a in assignments if not a.get("submitted")]
    print(f"{len(pending)} pending assignments.\n")

    if force:
        print("(--force: ignoring cache)\n")

    est = AssignmentEstimator()
    results = est.estimate_all(pending, force=force)

    total = 0
    for a in pending:
        r = results.get(a["uuid"], {})
        hours = r.get("total_hours") or 0
        total += hours

        type_tag = r.get("type", "?").upper()
        print(f"┌─ {a['name']}")
        print(f"│  Due {a['due']}   {a['course_code']}   Weight {a.get('weightage','-')}%"
              f"   {'[GROUP]' if a.get('is_group') else ''}")
        print(f"│  [{type_tag}]  {hours}h  ({r.get('confidence','?')}, "
              f"{r.get('intensity','?')})  →  {r.get('session_count',0)} × "
              f"{r.get('session_length_minutes',0)}min")

        print(f"│  Deliverables:")
        for d in r.get("deliverables") or []:
            print(f"│    · {d['minutes']:>4}min  [{d.get('kind','?'):<11}]  {d['name']}")
        print("└─\n")

    print(f"TOTAL across {len(pending)} pending: {total:.1f} hours")
    if pending:
        print(f"Average: {total/len(pending):.1f}h per assignment")