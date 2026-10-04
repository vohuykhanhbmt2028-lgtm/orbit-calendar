"""ORBIT Calendar — the document editor.

Launch:
    python calendar_app.py                    # opens Home view
    python calendar_app.py path/to/file.orbit # opens that document
"""

import os
import sys
import json
import calendar as pycal
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from datetime import datetime, date, timedelta

import documents
import dated_events
import completions
import subprocess


def bring_to_front(root):
    """Force the calendar window to appear in front on macOS."""
    root.lift()
    root.attributes('-topmost', True)
    root.after(200, lambda: root.attributes('-topmost', False))
    root.focus_force()

    if sys.platform == 'darwin':
        try:
            script = (
                'tell application "System Events" to set frontmost of '
                '(first process whose unix id is {}) to true'
            ).format(os.getpid())
            subprocess.Popen(['osascript', '-e', script],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
PAPER        = '#faf8f5'
PAPER_ALT    = '#f2eee7'
PAPER_CARD   = '#ffffff'
PAPER_ADJ    = '#f6f3ee'
INK          = '#1a1715'
INK_SOFT     = '#6e6559'
INK_FAINT    = '#a59c8e'
RULE         = '#e6e1d6'
RULE_FAINT   = '#eeeae1'
ORBIT        = '#b01b1b'
ORBIT_DEEP   = '#7d1212'
ORBIT_WASH   = '#fbf3f2'
SELECT_FILL  = '#1a1715'
SELECT_CELL  = '#f1ede6'

F_SERIF = 'Georgia'
F_SANS  = 'Helvetica Neue'
F_MONO  = 'Courier New'


def letterspace(s, gap=' '):
    return gap.join(list(s))


def format_time(hour, minute):
    if hour == 0:  return f"12:{minute:02d} AM"
    if hour < 12:  return f"{hour}:{minute:02d} AM"
    if hour == 12: return f"12:{minute:02d} PM"
    return f"{hour-12}:{minute:02d} PM"


def time_key(t):
    try:
        return datetime.strptime(t, '%I:%M %p')
    except Exception:
        return datetime.min


def parse_time(t):
    try:
        dt = datetime.strptime(t.strip().upper(), '%I:%M %p')
        return dt.hour, dt.minute
    except Exception:
        return 9, 0


def weekday_of(d):
    return ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday'][d.weekday()]


def parse_date_string(s):
    s = s.strip().lower()
    if not s:
        return None
    today = datetime.now().date()
    if s == 'today':     return today
    if s == 'tomorrow':  return today + timedelta(days=1)
    if s == 'yesterday': return today - timedelta(days=1)
    cleaned = s.replace(',', '').strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%m-%d-%Y',
                '%b %d %Y', '%B %d %Y', '%d %b %Y', '%d %B %Y'):
        try: return datetime.strptime(cleaned, fmt).date()
        except ValueError: pass
    for fmt in ('%m/%d', '%m-%d', '%b %d', '%B %d'):
        try:
            d = datetime.strptime(cleaned, fmt).date()
            return date(today.year, d.month, d.day)
        except ValueError: pass
    return None


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
CALENDARS = [
    ('Classes',     ['class', 'lecture', 'seminar', 'math', 'bio', 'chem',
                     'physics', 'japanese', 'english', 'history', 'econ', 'lab'],
     '#3d4b7a'),
    ('Assignments', ['assignment', 'due', 'submit', 'deliverable'],
     '#a83e1f'),
    ('Gym',         ['gym', 'exercise', 'run', 'workout', 'yoga', 'sport', 'train'],
     '#3f6b4a'),
    ('Work',        ['work', 'job', 'shift'],
     '#a06a2c'),
    ('Study',       ['study', 'read', 'homework', 'exam', 'review'],
     '#8a2c2c'),
    ('Meetings',    ['meeting', 'call', 'appointment', 'therapy'],
     '#6b3d6b'),
    ('Meals',       ['breakfast', 'lunch', 'dinner', 'meal', 'eat', 'coffee'],
     '#b8823d'),
    ('Rest',        ['sleep', 'rest', 'wind', 'free', 'break'],
     '#6b7280'),
]
OTHER_CAL = ('Other', ORBIT)


def classify(text):
    t = text.lower()
    for name, kws, _ in CALENDARS:
        if any(k in t for k in kws):
            return name
    return OTHER_CAL[0]


def classify_event(ev):
    if ev.get('calendar'):
        return ev['calendar']
    return classify(ev.get('activity', ''))


def color_of(name):
    for n, _kws, color in CALENDARS:
        if n == name:
            return color
    return OTHER_CAL[1]


# ---------------------------------------------------------------------------
# Main window — becomes the editor
# ---------------------------------------------------------------------------
class CalendarApp:
    def __init__(self, root, initial_path=None):
        self.root = root
        self.root.title("ORBIT Calendar")
        self.root.geometry("1360x880")
        self.root.minsize(1140, 720)
        self.root.configure(bg=PAPER)

        self.schedule = {}
        self.variant_name = ''
        self.current_file_path = None
        self.is_dirty = False

        # LMS data (dated events + their estimates)
        self.dated_events = dated_events.load_events()
        self.estimates = dated_events.load_estimates()
        self.completions = completions.all_entries()

        self.view_mode = 'month'
        self.sidebar_visible = True
        self.visible_calendars = {n for n, _, _ in CALENDARS} | {OTHER_CAL[0]}
        self.search_text = ''
        self.selected_event = None
        self.undo_stack = []
        self.redo_stack = []
        self._drag = None
        self.ROW_H = 46

        today = datetime.now().date()
        self.view_year  = today.year
        self.view_month = today.month
        self.selected_date = today

        self._setup_menu()
        self._build()

        if initial_path and os.path.exists(initial_path):
            self._load_file(initial_path)

        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self._bind_shortcuts()
        self._render_all()

    # =====================================================================
    # Menu
    # =====================================================================
    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        app_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ORBIT Calendar", menu=app_menu)
        app_menu.add_command(label="About ORBIT Calendar",
                              command=self._about)
        app_menu.add_separator()
        app_menu.add_command(label="Quit ORBIT Calendar",
                              command=self._on_quit, accelerator="Cmd+Q")

        fm = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=fm)
        fm.add_command(label="Open…", command=self._open,
                        accelerator="Cmd+O")
        fm.add_command(label="Refresh from LMS",
                        command=self._refresh_from_lms,
                        accelerator="Cmd+R")
        fm.add_command(label="Study Log…",
                        command=self._show_study_log)
        fm.add_separator()
        fm.add_command(label="Save", command=self._save,
                        accelerator="Cmd+S")
        fm.add_command(label="Save As…", command=self._save_as,
                        accelerator="Shift+Cmd+S")
        fm.add_separator()
        fm.add_command(label="Close Window",
                        command=self._on_quit, accelerator="Cmd+W")

        vm = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=vm)
        vm.add_command(label="Day",
                        command=lambda: self._set_view('day'),
                        accelerator="Cmd+1")
        vm.add_command(label="Week",
                        command=lambda: self._set_view('week'),
                        accelerator="Cmd+2")
        vm.add_command(label="Month",
                        command=lambda: self._set_view('month'),
                        accelerator="Cmd+3")
        vm.add_command(label="Year",
                        command=lambda: self._set_view('year'),
                        accelerator="Cmd+4")

    def _bind_shortcuts(self):
        r = self.root
        r.bind('<Command-s>', lambda e: self._save())
        r.bind('<Command-Shift-S>', lambda e: self._save_as())
        r.bind('<Command-o>', lambda e: self._open())
        r.bind('<Command-r>', lambda e: self._refresh_from_lms())
        r.bind('<Command-z>', lambda e: self._undo())
        r.bind('<Command-Shift-Z>', lambda e: self._redo())
        r.bind('<Command-n>', lambda e: self._new_event_on_selected())
        r.bind('<Delete>', lambda e: self._delete_selected())
        r.bind('<BackSpace>', lambda e: self._delete_selected())
        r.bind('<Command-1>', lambda e: self._set_view('day'))
        r.bind('<Command-2>', lambda e: self._set_view('week'))
        r.bind('<Command-3>', lambda e: self._set_view('month'))
        r.bind('<Command-4>', lambda e: self._set_view('year'))

    # =====================================================================
    # LMS refresh
    # =====================================================================
    def _refresh_from_lms(self):
        """Run the orchestrator to pull fresh data from Coach LMS."""
        if self.is_dirty and not self._prompt_save():
            return

        self.root.config(cursor="watch")
        self.root.update_idletasks()
        self.status.config(text="Refreshing from LMS… (this may take 15–60s)")
        self.root.update_idletasks()

        ok, message = dated_events.refresh_from_lms()

        self.root.config(cursor="")
        if not ok:
            self.status.config(text=f"LMS refresh failed: {message}")
            messagebox.showerror("Refresh Failed", message)
            return

        # Reload everything
        self.dated_events = dated_events.load_events()
        self.estimates = dated_events.load_estimates()

        n_classes = sum(1 for e in self.dated_events
                        if e.get("calendar") == "Classes")
        n_asg = sum(1 for e in self.dated_events
                    if e.get("calendar") == "Assignments")
        self.status.config(
            text=f"Refreshed: {n_classes} sessions · {n_asg} assignments")
        self._render_all()

    def _show_study_log(self):
        """Show a summary of completed/skipped events + personal multiplier."""
        from datetime import timedelta
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week = completions.weekly_summary(week_start)
        life = completions.lifetime_counts()
        mult = completions.personal_multiplier()

        lines = [
            "This week",
            f"  ✓ Done     {week['done']}",
            f"  ◐ Partial  {week['partial']}",
            f"  ✗ Skipped  {week['skipped']}",
            "",
            "Lifetime",
            f"  ✓ Done     {life['done']}",
            f"  ◐ Partial  {life['partial']}",
            f"  ✗ Skipped  {life['skipped']}",
        ]

        if mult is not None:
            lines.append("")
            lines.append(f"Personal multiplier: {mult}×")
            if mult > 1.15:
                lines.append("  You tend to take longer than the estimate.")
            elif mult < 0.85:
                lines.append("  You tend to finish faster than the estimate.")
            else:
                lines.append("  Your pace matches the estimate.")
        else:
            lines.append("")
            lines.append("(Log 5+ sessions with hours to compute your")
            lines.append(" personal multiplier.)")

        messagebox.showinfo("Study Log", "\n".join(lines))

    def _dated_events_for(self, d):
        """Return dated events (from LMS) matching a specific date."""
        date_str = d.strftime("%Y-%m-%d")
        return [e for e in self.dated_events if e.get("date") == date_str]
    
    def _completion_for(self, event_id, date_str):
        """Look up a completion entry. Refreshes from disk first."""
        self.completions = completions.all_entries()
        return self.completions.get(f"{event_id}|{date_str}")

    def _mark_event(self, event_id, date_str, activity,
                    planned_minutes=None, source=None):
        """Prompt for done/skipped/partial, then optionally hours."""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="✓  Done",
                          command=lambda: self._apply_mark(
                              event_id, date_str, activity,
                              "done", planned_minutes, source))
        menu.add_command(label="↷  Partial",
                          command=lambda: self._apply_mark(
                              event_id, date_str, activity,
                              "partial", planned_minutes, source))
        menu.add_command(label="✗  Skipped",
                          command=lambda: self._apply_mark(
                              event_id, date_str, activity,
                              "skipped", planned_minutes, source))
        existing = self._completion_for(event_id, date_str)
        if existing:
            menu.add_separator()
            menu.add_command(label="Clear log entry",
                              command=lambda: self._clear_mark(
                                  event_id, date_str))
        try:
            menu.tk_popup(self.root.winfo_pointerx(),
                          self.root.winfo_pointery())
        finally:
            menu.grab_release()

    def _apply_mark(self, event_id, date_str, activity,
                    status, planned_minutes, source):
        actual = None
        if status == "done":
            from tkinter import simpledialog
            ans = messagebox.askyesno(
                "Log hours?",
                f"Marked done.\n\nDo you want to log how long it took?")
            if ans:
                mins = simpledialog.askinteger(
                    "Hours spent",
                    "How many minutes did this actually take?",
                    minvalue=5, maxvalue=600,
                    parent=self.root)
                if mins:
                    actual = mins
        completions.log(
            event_id=event_id,
            date_str=date_str,
            activity=activity,
            status=status,
            planned_minutes=planned_minutes,
            actual_minutes=actual,
            source=source,
        )
        self.completions = completions.all_entries()
        self._render_all()

    def _clear_mark(self, event_id, date_str):
        completions.clear(event_id, date_str)
        self.completions = completions.all_entries()
        self._render_all()

    def _chip_menu(self, event, d, chip):
        """Compact menu shown when a chip is clicked."""
        event_id = chip.get("id") or ""
        date_str = d.strftime("%Y-%m-%d")
        activity = chip.get("activity", "")
        source = chip.get("source", "template")
        planned = chip.get("duration_min") or chip.get("planned_minutes")

        # If it's a dated event, look up richer metadata
        dated_ev = None
        if source == "dated":
            for e in self.dated_events:
                if e.get("id") == event_id:
                    dated_ev = e
                    break
            if dated_ev:
                planned = dated_ev.get("duration_min") or planned

        # Already logged?
        completion = self._completion_for(event_id, date_str)

        menu = tk.Menu(self.root, tearoff=0)

        # --- Open ---
        if source == "dated":
            menu.add_command(
                label="Open details",
                command=lambda: self._open_dated_event(d, event_id))
        else:
            menu.add_command(
                label="Open in inspector",
                command=lambda: self._select_event_click(None, d, event_id))
        menu.add_separator()

        # --- Mark ---
        def mark(status):
            self._apply_mark(event_id, date_str, activity,
                             status, planned, source)

        menu.add_command(label="✓   Mark done",     command=lambda: mark("done"))
        menu.add_command(label="◐   Mark partial",  command=lambda: mark("partial"))
        menu.add_command(label="✗   Mark skipped",  command=lambda: mark("skipped"))

        if completion:
            menu.add_separator()
            menu.add_command(label="Clear log entry",
                             command=lambda: self._clear_mark(event_id, date_str))

        # --- Edit (template only) ---
        if source == "template":
            menu.add_separator()
            menu.add_command(
                label="Duplicate",
                command=lambda: self._duplicate_event(weekday_of(d), event_id))
            menu.add_command(
                label="Delete",
                command=lambda: self._delete_event(weekday_of(d), event_id))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_dated_event(self, date, event_id):
        """Show details for a dated event (LMS-origin)."""
        ev = None
        for e in self.dated_events:
            if e.get("id") == event_id:
                ev = e
                break
        if not ev:
            return

        lines = [
            ev.get("activity", "Untitled"),
            "",
            f"Date: {ev.get('date', '')}",
            f"Time: {ev.get('time', 'All day')}",
        ]
        if ev.get("course"):
            lines.append(f"Course: {ev['course']}")
        if ev.get("course_code"):
            lines.append(f"Code: {ev['course_code']}")
        if ev.get("weightage"):
            lines.append(f"Weightage: {ev['weightage']}%")
        if ev.get("meeting_link"):
            lines.append(f"Link: {ev['meeting_link']}")

        # Try to find the estimate for assignments
        uuid = (ev.get("id") or "").replace("asg-", "", 1)
        est = None
        for k, v in self.estimates.items():
            if k.startswith(uuid + ":"):
                est = v
                break
        if est and est.get("total_hours"):
            lines.append("")
            lines.append(f"Estimated work: {est['total_hours']}h"
                         f"  ({est.get('confidence', '?')}, {est.get('intensity', '?')})")
            if est.get("phases"):
                lines.append("Breakdown:")
                for p in est["phases"]:
                    lines.append(f"  · {p['name']}: {p['hours']}h")
            if est.get("reasoning"):
                lines.append("")
                lines.append(f"Note: {est['reasoning']}")

        messagebox.showinfo("Event", "\n".join(lines))

    # =====================================================================
    # File operations
    # =====================================================================
    def _load_file(self, path):
        try:
            data = documents.load_document(path)
        except Exception as e:
            messagebox.showerror("Open Error", f"Failed to open:\n{e}")
            return
        self.schedule = data.get('schedule', {}) or {}
        self.variant_name = data.get('variant_name', '') or ''
        self.current_file_path = path
        self.is_dirty = False
        self._ensure_ids()
        self._update_title()
        self._render_all()

    def _open(self):
        if not self._prompt_save():
            return
        path = filedialog.askopenfilename(
            title="Open Calendar",
            filetypes=[("ORBIT Calendar", "*.orbit"), ("All files", "*.*")])
        if not path:
            return
        self._load_file(path)

    def _save(self):
        if not self.current_file_path:
            self._save_as()
            return
        self._write(self.current_file_path)

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Calendar",
            defaultextension=".orbit",
            filetypes=[("ORBIT Calendar", "*.orbit"), ("All files", "*.*")])
        if not path:
            return
        self._write(path)
        self.current_file_path = path
        self._update_title()

    def _write(self, path):
        payload = {
            'schedule': self.schedule,
            'variant_name': self.variant_name,
        }
        try:
            documents.save_document(path, payload)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save:\n{e}")
            return
        self.is_dirty = False
        self._update_title()

    def _update_title(self):
        if self.current_file_path:
            name = os.path.basename(self.current_file_path)
        else:
            name = "Untitled"
        prefix = "\u2022 " if self.is_dirty else ""
        self.root.title(f"{prefix}{name} — ORBIT Calendar")

    def _mark_dirty(self):
        if not self.is_dirty:
            self.is_dirty = True
            self._update_title()

    def _prompt_save(self):
        if not self.is_dirty:
            return True
        name = (os.path.basename(self.current_file_path)
                if self.current_file_path else "Untitled")
        answer = messagebox.askyesnocancel(
            "Unsaved Changes",
            f"Save changes to \u201c{name}\u201d before closing?")
        if answer is None:
            return False
        if answer is True:
            self._save()
            return not self.is_dirty
        return True

    def _on_quit(self):
        if not self._prompt_save():
            return
        self.root.destroy()

    def _about(self):
        messagebox.showinfo(
            "About ORBIT Calendar",
            "ORBIT Calendar\n\n"
            "A quiet place to plan your week.\n\n"
            "Day · Week · Month · Year views\n"
            "Drag on the timeline to create events.\n"
            "File → Refresh from LMS to pull Coach LMS data."
        )

    # =====================================================================
    # Undo / redo
    # =====================================================================
    def _snapshot(self):
        import copy
        return copy.deepcopy(self.schedule)

    def _push_undo(self, _desc=''):
        self.undo_stack.append(self._snapshot())
        if len(self.undo_stack) > 60:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _undo(self):
        if not self.undo_stack:
            return
        current = self._snapshot()
        snap = self.undo_stack.pop()
        self.redo_stack.append(current)
        self.schedule = snap
        self._mark_dirty()
        self._render_all()

    def _redo(self):
        if not self.redo_stack:
            return
        current = self._snapshot()
        snap = self.redo_stack.pop()
        self.undo_stack.append(current)
        self.schedule = snap
        self._mark_dirty()
        self._render_all()

    # =====================================================================
    # Event operations
    # =====================================================================
    def _ensure_ids(self):
        import uuid
        for day, events in self.schedule.items():
            for ev in events:
                if 'id' not in ev or not ev['id']:
                    ev['id'] = uuid.uuid4().hex[:8]

    def _add_event(self, day_name, hour, minute, duration_min=60,
                   activity='New event', focus_editor=True):
        import uuid
        ev = {
            'id': uuid.uuid4().hex[:8],
            'time': format_time(hour, minute),
            'activity': activity,
            'duration_min': duration_min,
        }
        self._push_undo('Add event')
        self.schedule.setdefault(day_name, []).append(ev)
        self.selected_event = (day_name, ev['id'])
        self._mark_dirty()
        self._render_all()
        if focus_editor:
            self.root.after(60, self._focus_activity_entry)

    def _delete_event(self, day_name, event_id):
        self._push_undo('Delete event')
        self.schedule[day_name] = [
            ev for ev in self.schedule.get(day_name, [])
            if ev.get('id') != event_id
        ]
        if self.selected_event == (day_name, event_id):
            self.selected_event = None
        self._mark_dirty()
        self._render_all()

    def _duplicate_event(self, day_name, event_id):
        import uuid
        self._push_undo('Duplicate event')
        source = None
        for ev in self.schedule.get(day_name, []):
            if ev.get('id') == event_id:
                source = ev
                break
        if not source:
            return
        hh, mm = parse_time(source.get('time', '9:00 AM'))
        hh = min(hh + 1, 22)
        new_ev = {
            'id': uuid.uuid4().hex[:8],
            'time': format_time(hh, mm),
            'activity': source.get('activity', ''),
            'duration_min': source.get('duration_min', 60),
        }
        if source.get('calendar'):
            new_ev['calendar'] = source['calendar']
        self.schedule[day_name].append(new_ev)
        self.selected_event = (day_name, new_ev['id'])
        self._mark_dirty()
        self._render_all()

    def _selected_event_obj(self):
        if not self.selected_event:
            return None
        day_name, event_id = self.selected_event
        for ev in self.schedule.get(day_name, []):
            if ev.get('id') == event_id:
                return ev, day_name
        return None

    def _delete_selected(self):
        if not self.selected_event:
            return
        day_name, event_id = self.selected_event
        self._delete_event(day_name, event_id)

    def _new_event_on_selected(self):
        self._add_event(weekday_of(self.selected_date), 9, 0)

    def _select_event_click(self, _event, d, event_id):
        self.selected_event = (weekday_of(d), event_id)
        self.selected_date = d
        self._render_all()
        return "break"

    # =====================================================================
    # Build
    # =====================================================================
    def _build(self):
        self._build_toolbar()

        self.body = tk.Frame(self.root, bg=PAPER)
        self.body.pack(fill=tk.BOTH, expand=True)
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(2, weight=1)

        self.sidebar = tk.Frame(self.body, bg=PAPER_ALT, width=240)
        self.sidebar.grid(row=0, column=0, sticky='ns')
        self.sidebar.grid_propagate(False)

        self.sidebar_border = tk.Frame(self.body, bg=RULE, width=1)
        self.sidebar_border.grid(row=0, column=1, sticky='ns')

        self.main = tk.Frame(self.body, bg=PAPER)
        self.main.grid(row=0, column=2, sticky='nsew')

        self.inspector_border = tk.Frame(self.body, bg=RULE, width=1)
        self.inspector = tk.Frame(self.body, bg=PAPER_ALT, width=280)
        self.inspector.grid_propagate(False)

        self._build_footer()

    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=PAPER, height=64)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=PAPER)
        left.pack(side=tk.LEFT, padx=(28, 0))

        seg_bg = tk.Frame(left, bg=RULE_FAINT)
        seg_bg.pack(pady=16)

        self.seg_buttons = {}
        for mode, label in [('day', 'Day'), ('week', 'Week'),
                             ('month', 'Month'), ('year', 'Year')]:
            lbl = tk.Label(seg_bg, text=label,
                           font=(F_SANS, 10, 'bold'),
                           bg=RULE_FAINT, fg=INK_SOFT,
                           padx=14, pady=5, cursor='hand2')
            lbl.pack(side=tk.LEFT)
            lbl.bind('<Button-1>', lambda e, m=mode: self._set_view(m))
            self.seg_buttons[mode] = lbl

        center = tk.Frame(bar, bg=PAPER)
        center.pack(side=tk.LEFT, expand=True)

        inner = tk.Frame(center, bg=PAPER)
        inner.pack()

        prev = tk.Label(inner, text="\u2039", font=(F_SERIF, 22),
                        bg=PAPER, fg=INK_FAINT, padx=8, cursor='hand2')
        prev.pack(side=tk.LEFT)
        prev.bind('<Button-1>', lambda e: self._shift(-1))
        prev.bind('<Enter>', lambda e: prev.config(fg=INK))
        prev.bind('<Leave>', lambda e: prev.config(fg=INK_FAINT))

        self.title_lbl = tk.Label(inner, text="", font=(F_SERIF, 17, 'bold'),
                                   bg=PAPER, fg=INK, padx=10)
        self.title_lbl.pack(side=tk.LEFT)

        nxt = tk.Label(inner, text="\u203a", font=(F_SERIF, 22),
                       bg=PAPER, fg=INK_FAINT, padx=8, cursor='hand2')
        nxt.pack(side=tk.LEFT)
        nxt.bind('<Button-1>', lambda e: self._shift(+1))
        nxt.bind('<Enter>', lambda e: nxt.config(fg=INK))
        nxt.bind('<Leave>', lambda e: nxt.config(fg=INK_FAINT))

        self.today_pill = tk.Label(inner, text="Today",
                                    font=(F_SANS, 9, 'bold'),
                                    bg=PAPER, fg=ORBIT,
                                    padx=0, pady=3, cursor='hand2')
        self.today_pill.pack(side=tk.LEFT, padx=(20, 0))
        self.today_pill.bind('<Button-1>', lambda e: self._goto_today())

        jump_frame = tk.Frame(bar, bg=PAPER, highlightthickness=1,
                               highlightbackground=RULE,
                               highlightcolor=ORBIT)
        jump_frame.pack(side=tk.RIGHT, padx=(0, 12), pady=16)

        tk.Label(jump_frame, text="\u2192",
                 font=(F_SANS, 11), bg=PAPER, fg=INK_FAINT)\
            .pack(side=tk.LEFT, padx=(8, 0))

        self.jump_entry = tk.Entry(jump_frame, font=(F_MONO, 10),
                                    bg=PAPER, fg=INK,
                                    relief='flat', bd=0,
                                    width=14, insertbackground=INK)
        self.jump_entry.pack(side=tk.LEFT, ipady=5, padx=(4, 8))
        self.jump_entry.bind('<Return>', self._on_jump)
        self._jump_placeholder = "jump to date"
        self._show_jump_placeholder()

        tk.Frame(self.root, bg=RULE, height=1).pack(fill=tk.X)

    def _show_jump_placeholder(self):
        if not self.jump_entry.get():
            self.jump_entry.insert(0, self._jump_placeholder)
            self.jump_entry.config(fg=INK_FAINT)
        self.jump_entry.bind('<FocusIn>', self._clear_jump_placeholder)
        self.jump_entry.bind('<FocusOut>', self._restore_jump_placeholder)

    def _clear_jump_placeholder(self, _e):
        if self.jump_entry.get() == self._jump_placeholder:
            self.jump_entry.delete(0, 'end')
            self.jump_entry.config(fg=INK)

    def _restore_jump_placeholder(self, _e):
        if not self.jump_entry.get():
            self.jump_entry.insert(0, self._jump_placeholder)
            self.jump_entry.config(fg=INK_FAINT)

    def _on_jump(self, _e):
        text = self.jump_entry.get().strip()
        if not text or text == self._jump_placeholder:
            return
        d = parse_date_string(text)
        if not d:
            return
        self.selected_date = d
        self.view_year = d.year
        self.view_month = d.month
        self._render_all()
        self.jump_entry.delete(0, 'end')
        self._restore_jump_placeholder()
        self.root.focus_set()

    def _build_footer(self):
        f = tk.Frame(self.root, bg=PAPER, height=26)
        f.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Frame(f, bg=RULE_FAINT, height=1).pack(fill=tk.X, side=tk.TOP)

        inner = tk.Frame(f, bg=PAPER)
        inner.pack(fill=tk.X)

        self.status = tk.Label(inner, text="", font=(F_SANS, 9),
                                bg=PAPER, fg=INK_FAINT, anchor='w')
        self.status.pack(side=tk.LEFT, padx=28, pady=4)

        self.path_lbl = tk.Label(inner, text="",
                                  font=(F_MONO, 9),
                                  bg=PAPER, fg='#cfc7b9', anchor='e')
        self.path_lbl.pack(side=tk.RIGHT, padx=28, pady=4)

    # =====================================================================
    # Events / filters
    # =====================================================================
    def events_for(self, d):
        """Template events (from schedule.json) for a date's weekday."""
        events = self.schedule.get(weekday_of(d), []) or []
        out = [ev for ev in events
               if classify_event(ev) in self.visible_calendars]
        out.sort(key=lambda e: time_key(e.get('time', '')))
        return out

    def matches_search(self, ev):
        if not self.search_text:
            return True
        return self.search_text.lower() in ev.get('activity', '').lower()

    # =====================================================================
    # Sidebar
    # =====================================================================
    def _render_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        head = tk.Frame(self.sidebar, bg=PAPER_ALT)
        head.pack(fill=tk.X, padx=18, pady=(20, 8))

        tk.Label(head, text=letterspace("MONTH"),
                 font=(F_SANS, 8, 'bold'),
                 bg=PAPER_ALT, fg=INK_FAINT).pack(side=tk.LEFT)

        nxt = tk.Label(head, text="\u203a", font=(F_SERIF, 14),
                       bg=PAPER_ALT, fg=INK_FAINT, cursor='hand2', padx=4)
        nxt.pack(side=tk.RIGHT)
        nxt.bind('<Button-1>', lambda e: self._shift(+1))

        prev = tk.Label(head, text="\u2039", font=(F_SERIF, 14),
                        bg=PAPER_ALT, fg=INK_FAINT, cursor='hand2', padx=4)
        prev.pack(side=tk.RIGHT)
        prev.bind('<Button-1>', lambda e: self._shift(-1))

        tk.Label(self.sidebar,
                 text=f"{pycal.month_name[self.view_month]} {self.view_year}",
                 font=(F_SERIF, 14, 'bold'),
                 bg=PAPER_ALT, fg=INK).pack(anchor='w', padx=18, pady=(0, 10))

        mg = tk.Frame(self.sidebar, bg=PAPER_ALT)
        mg.pack(fill=tk.X, padx=18, pady=(0, 18))
        for i in range(7):
            mg.columnconfigure(i, weight=1, uniform='mini')
        for i, name in enumerate(['M', 'T', 'W', 'T', 'F', 'S', 'S']):
            tk.Label(mg, text=name, font=(F_SANS, 8, 'bold'),
                     bg=PAPER_ALT, fg=INK_FAINT)\
                .grid(row=0, column=i, sticky='nsew')

        pycal.setfirstweekday(pycal.MONDAY)
        matrix = pycal.monthcalendar(self.view_year, self.view_month)
        today = datetime.now().date()

        for r, week in enumerate(matrix, start=1):
            for c, dn in enumerate(week):
                if dn == 0:
                    tk.Label(mg, text="", bg=PAPER_ALT).grid(row=r, column=c)
                    continue
                d = date(self.view_year, self.view_month, dn)
                is_today = (d == today)
                is_selected = (d == self.selected_date)
                if is_today: bg, fg = ORBIT, '#ffffff'
                elif is_selected: bg, fg = SELECT_FILL, '#ffffff'
                else: bg, fg = PAPER_ALT, INK
                cell = tk.Label(mg, text=str(dn),
                                font=(F_SERIF, 9,
                                      'bold' if (is_today or is_selected) else 'normal'),
                                bg=bg, fg=fg, cursor='hand2', width=2, pady=2)
                cell.grid(row=r, column=c, sticky='nsew', padx=1, pady=1)
                cell.bind('<Button-1>', lambda e, dd=d: self._select_day(dd))

        tk.Frame(self.sidebar, bg=RULE, height=1)\
            .pack(fill=tk.X, padx=18, pady=(0, 14))

        hdr = tk.Frame(self.sidebar, bg=PAPER_ALT)
        hdr.pack(fill=tk.X, padx=18, pady=(0, 8))
        tk.Label(hdr, text=letterspace("CALENDARS"),
                 font=(F_SANS, 8, 'bold'),
                 bg=PAPER_ALT, fg=INK_FAINT).pack(side=tk.LEFT)
        show_all = tk.Label(hdr, text="All", font=(F_SANS, 9),
                             bg=PAPER_ALT, fg=ORBIT, cursor='hand2')
        show_all.pack(side=tk.RIGHT)
        show_all.bind('<Button-1>', lambda e: self._toggle_all())

        for name, _kws, color in CALENDARS:
            self._render_cal_row(name, color)
        self._render_cal_row(*OTHER_CAL)

    def _render_cal_row(self, name, color):
        visible = name in self.visible_calendars
        row = tk.Frame(self.sidebar, bg=PAPER_ALT, cursor='hand2')
        row.pack(fill=tk.X, padx=18, pady=3)
        chk = tk.Canvas(row, width=14, height=14,
                        bg=PAPER_ALT, highlightthickness=0, bd=0, cursor='hand2')
        chk.pack(side=tk.LEFT, padx=(0, 10))
        chk.create_rectangle(1, 1, 13, 13,
                              outline=color if visible else RULE,
                              fill=color if visible else PAPER_ALT)
        if visible:
            chk.create_line(4, 7, 6, 10, 11, 4, fill='#ffffff', width=2)
        lbl = tk.Label(row, text=name, font=(F_SANS, 11),
                       bg=PAPER_ALT, fg=INK if visible else INK_FAINT,
                       anchor='w', cursor='hand2')
        lbl.pack(side=tk.LEFT, fill='x', expand=True)

        def toggle(_e):
            if name in self.visible_calendars:
                self.visible_calendars.remove(name)
            else:
                self.visible_calendars.add(name)
            self._render_sidebar()
            self._render_main()

        for w in (row, chk, lbl):
            w.bind('<Button-1>', toggle)

    def _toggle_all(self):
        all_names = {n for n, _, _ in CALENDARS} | {OTHER_CAL[0]}
        self.visible_calendars = (set() if self.visible_calendars == all_names
                                   else all_names)
        self._render_sidebar()
        self._render_main()

    # =====================================================================
    # Inspector
    # =====================================================================
    def _render_inspector(self):
        if not self.selected_event or not self._selected_event_obj():
            self.inspector.grid_remove()
            self.inspector_border.grid_remove()
            return
        self.inspector.grid(row=0, column=4, sticky='ns')
        self.inspector_border.grid(row=0, column=3, sticky='ns')
        self._build_inspector()

    def _build_inspector(self):
        for w in self.inspector.winfo_children():
            w.destroy()
        top = tk.Frame(self.inspector, bg=PAPER_ALT)
        top.pack(fill=tk.X, padx=18, pady=(20, 4))
        tk.Label(top, text=letterspace("EVENT"),
                 font=(F_SANS, 8, 'bold'),
                 bg=PAPER_ALT, fg=INK_FAINT).pack(side=tk.LEFT)
        close = tk.Label(top, text="\u00d7", font=(F_SERIF, 18),
                          bg=PAPER_ALT, fg=INK_FAINT, cursor='hand2')
        close.pack(side=tk.RIGHT)
        close.bind('<Button-1>', lambda e: self._close_inspector())

        obj = self._selected_event_obj()
        if not obj: return
        ev, day_name = obj

        af = tk.Frame(self.inspector, bg=PAPER_ALT)
        af.pack(fill=tk.X, padx=18, pady=(16, 0))
        self.ins_activity_var = tk.StringVar(value=ev.get('activity', ''))
        self.ins_activity_entry = tk.Entry(
            af, textvariable=self.ins_activity_var,
            font=(F_SERIF, 15), bg=PAPER_ALT, fg=INK,
            relief='flat', bd=0, highlightthickness=0, insertbackground=INK)
        self.ins_activity_entry.pack(fill=tk.X, ipady=4)
        self.ins_activity_entry.bind('<Return>', self._commit_activity)
        self.ins_activity_entry.bind('<FocusOut>', self._commit_activity)

        tk.Frame(self.inspector, bg=RULE_FAINT, height=1)\
            .pack(fill=tk.X, padx=18, pady=(6, 16))

        self._inspector_field("TIME")
        self.ins_time_var = tk.StringVar(value=ev.get('time', ''))
        self.ins_time_entry = tk.Entry(
            self.inspector, textvariable=self.ins_time_var,
            font=(F_MONO, 11), bg=PAPER_ALT, fg=INK,
            relief='flat', bd=0, highlightthickness=0, insertbackground=INK)
        self.ins_time_entry.pack(fill=tk.X, padx=18, ipady=3)
        self.ins_time_entry.bind('<Return>', self._commit_time)
        self.ins_time_entry.bind('<FocusOut>', self._commit_time)

        self._inspector_field("DAY", top_pad=16)
        self.ins_day_var = tk.StringVar(value=day_name)
        day_box = ttk.Combobox(self.inspector, textvariable=self.ins_day_var,
                                values=['Monday', 'Tuesday', 'Wednesday',
                                        'Thursday', 'Friday', 'Saturday', 'Sunday'],
                                state='readonly', width=18)
        day_box.pack(anchor='w', padx=18)
        day_box.bind('<<ComboboxSelected>>', self._commit_day)

        self._inspector_field("CALENDAR", top_pad=16)
        self.ins_cal_var = tk.StringVar(value=classify_event(ev))
        cat_box = ttk.Combobox(self.inspector, textvariable=self.ins_cal_var,
                                values=[n for n, _, _ in CALENDARS] + [OTHER_CAL[0]],
                                state='readonly', width=18)
        cat_box.pack(anchor='w', padx=18)
        cat_box.bind('<<ComboboxSelected>>', self._commit_calendar)

        self._inspector_field("DURATION (MIN)", top_pad=16)
        self.ins_dur_var = tk.StringVar(value=str(ev.get('duration_min', 60)))
        dur_box = ttk.Combobox(self.inspector, textvariable=self.ins_dur_var,
                                values=['15', '30', '45', '60', '90', '120'],
                                state='readonly', width=18)
        dur_box.pack(anchor='w', padx=18)
        dur_box.bind('<<ComboboxSelected>>', self._commit_duration)

        tk.Frame(self.inspector, bg=RULE_FAINT, height=1)\
            .pack(fill=tk.X, padx=18, pady=(24, 16))

        def action(label, cmd, color=INK_SOFT):
            lbl = tk.Label(self.inspector, text=label,
                           font=(F_SANS, 10, 'bold'),
                           bg=PAPER_ALT, fg=color, cursor='hand2', anchor='w')
            lbl.pack(fill=tk.X, padx=18, pady=3)
            lbl.bind('<Button-1>', lambda e: cmd())

        action("Duplicate", lambda: self._duplicate_event(day_name, ev['id']))
        action("Delete", lambda: self._delete_event(day_name, ev['id']), ORBIT)

    def _inspector_field(self, label, top_pad=0):
        wrap = tk.Frame(self.inspector, bg=PAPER_ALT)
        wrap.pack(fill=tk.X, padx=18, pady=(top_pad, 2))
        tk.Label(wrap, text=letterspace(label),
                 font=(F_SANS, 8, 'bold'),
                 bg=PAPER_ALT, fg=INK_FAINT).pack(anchor='w')

    def _focus_activity_entry(self):
        try:
            if (hasattr(self, 'ins_activity_entry')
                    and self.ins_activity_entry.winfo_exists()):
                self.ins_activity_entry.focus_set()
                self.ins_activity_entry.select_range(0, 'end')
        except tk.TclError:
            pass

    def _close_inspector(self):
        self.selected_event = None
        self._render_all()

    def _commit_activity(self, _e=None):
        obj = self._selected_event_obj()
        if not obj: return
        ev, day = obj
        new = self.ins_activity_var.get().strip() or 'Untitled'
        if ev.get('activity', '') == new: return
        self._push_undo()
        ev['activity'] = new
        self._mark_dirty()
        self._render_main()

    def _commit_time(self, _e=None):
        obj = self._selected_event_obj()
        if not obj: return
        ev, _ = obj
        text = self.ins_time_var.get().strip()
        try:
            dt = datetime.strptime(text.upper(), '%I:%M %p')
        except ValueError:
            self.ins_time_var.set(ev.get('time', ''))
            return
        new_time = format_time(dt.hour, dt.minute)
        if ev.get('time') == new_time: return
        self._push_undo()
        ev['time'] = new_time
        self._mark_dirty()
        self._render_main()

    def _commit_day(self, _e=None):
        obj = self._selected_event_obj()
        if not obj: return
        ev, old_day = obj
        new_day = self.ins_day_var.get()
        if new_day == old_day: return
        self._push_undo()
        self.schedule[old_day] = [
            x for x in self.schedule.get(old_day, []) if x.get('id') != ev['id']
        ]
        self.schedule.setdefault(new_day, []).append(ev)
        self.selected_event = (new_day, ev['id'])
        self._mark_dirty()
        self._render_all()

    def _commit_calendar(self, _e=None):
        obj = self._selected_event_obj()
        if not obj: return
        ev, _ = obj
        new_cat = self.ins_cal_var.get()
        if classify_event(ev) == new_cat: return
        self._push_undo()
        ev['calendar'] = new_cat
        self._mark_dirty()
        self._render_main()

    def _commit_duration(self, _e=None):
        obj = self._selected_event_obj()
        if not obj: return
        ev, _ = obj
        try: val = int(self.ins_dur_var.get())
        except ValueError: return
        if ev.get('duration_min', 60) == val: return
        self._push_undo()
        ev['duration_min'] = val
        self._mark_dirty()
        self._render_main()

    # =====================================================================
    # Context menus
    # =====================================================================
    def _popup(self, menu, event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _right_click_empty(self, event, d, hour=None):
        self.selected_date = d
        self.selected_event = None
        self._render_all()
        menu = tk.Menu(self.root, tearoff=0)
        if hour is not None:
            menu.add_command(label=f"New event at {hour:02d}:00",
                              command=lambda: self._add_event(weekday_of(d), hour, 0))
        else:
            menu.add_command(label=f"New event on {d.strftime('%b %d')}",
                              command=lambda: self._add_event(weekday_of(d), 9, 0))
        self._popup(menu, event)

    def _right_click_event(self, event, d, event_id):
        self.selected_event = (weekday_of(d), event_id)
        self.selected_date = d
        self._render_all()
        menu = tk.Menu(self.root, tearoff=0)

        # Mark options
        menu.add_command(
            label="Mark done",
            command=lambda: self._mark_event(
                event_id, d.strftime("%Y-%m-%d"),
                self._activity_for(event_id, d),
                self._planned_minutes_for(event_id, d),
                "template"))
        menu.add_command(
            label="Mark skipped",
            command=lambda: self._apply_mark(
                event_id, d.strftime("%Y-%m-%d"),
                self._activity_for(event_id, d), "skipped",
                self._planned_minutes_for(event_id, d), "template"))
        menu.add_separator()
        menu.add_command(label="Duplicate",
                          command=lambda: self._duplicate_event(
                              weekday_of(d), event_id))
        menu.add_command(label="Delete",
                          command=lambda: self._delete_event(
                              weekday_of(d), event_id))
        self._popup(menu, event)

    def _activity_for(self, event_id, d):
        for ev in self.schedule.get(weekday_of(d), []) or []:
            if ev.get("id") == event_id:
                return ev.get("activity", "")
        for ev in self._dated_events_for(d):
            if ev.get("id") == event_id:
                return ev.get("activity", "")
        return ""

    def _planned_minutes_for(self, event_id, d):
        for ev in self.schedule.get(weekday_of(d), []) or []:
            if ev.get("id") == event_id:
                return ev.get("duration_min")
        for ev in self._dated_events_for(d):
            if ev.get("id") == event_id:
                return ev.get("duration_min")
        return None

    # =====================================================================
    # Navigation
    # =====================================================================
    def _set_view(self, mode):
        self.view_mode = mode
        self._render_all()

    def _shift(self, delta):
        if self.view_mode == 'year':
            self.view_year += delta
        elif self.view_mode == 'month':
            self._shift_month(delta)
        elif self.view_mode == 'week':
            self.selected_date = self.selected_date + timedelta(days=7 * delta)
            self.view_month = self.selected_date.month
            self.view_year = self.selected_date.year
        elif self.view_mode == 'day':
            self.selected_date = self.selected_date + timedelta(days=delta)
            self.view_month = self.selected_date.month
            self.view_year = self.selected_date.year
        self._render_all()

    def _shift_month(self, delta):
        m = self.view_month + delta
        y = self.view_year
        while m < 1: m += 12; y -= 1
        while m > 12: m -= 12; y += 1
        self.view_month = m
        self.view_year = y

    def _goto_today(self):
        today = datetime.now().date()
        self.view_year = today.year
        self.view_month = today.month
        self.selected_date = today
        self._render_all()

    def _select_day(self, d):
        self.selected_date = d
        self.view_year = d.year
        self.view_month = d.month
        self._render_all()

    def _on_search(self, _e):
        self.search_text = self.search_entry.get().strip()
        self._render_main()

    # =====================================================================
    # Master render
    # =====================================================================
    def _render_all(self):
        self._render_segmented()
        self._render_title()
        self._render_sidebar()
        self._render_main()
        self._render_inspector()
        self._render_status()
        if self.sidebar_visible:
            self.sidebar.grid()
            self.sidebar_border.grid()
        else:
            self.sidebar.grid_remove()
            self.sidebar_border.grid_remove()

    def _render_segmented(self):
        for mode, lbl in self.seg_buttons.items():
            if mode == self.view_mode:
                lbl.config(bg=PAPER, fg=INK)
            else:
                lbl.config(bg=RULE_FAINT, fg=INK_SOFT)

    def _render_title(self):
        if self.view_mode == 'day':
            self.title_lbl.config(text=self.selected_date.strftime('%A, %B %d'))
        elif self.view_mode == 'week':
            start = self.selected_date - timedelta(days=self.selected_date.weekday())
            end = start + timedelta(days=6)
            if start.month == end.month:
                self.title_lbl.config(
                    text=f"{pycal.month_name[start.month]} {start.day}\u2013{end.day}")
            else:
                self.title_lbl.config(
                    text=f"{pycal.month_abbr[start.month]} {start.day} \u2013 "
                         f"{pycal.month_abbr[end.month]} {end.day}")
        elif self.view_mode == 'month':
            self.title_lbl.config(
                text=f"{pycal.month_name[self.view_month]} {self.view_year}")
        elif self.view_mode == 'year':
            self.title_lbl.config(text=str(self.view_year))

    def _render_status(self):
        total = sum(len(v) for v in self.schedule.values())
        n_lms = len(self.dated_events)
        if total == 0 and n_lms == 0:
            self.status.config(text="No events yet.")
        else:
            bits = []
            if total:
                bits.append(f"{total} template")
            if n_lms:
                bits.append(f"{n_lms} from LMS")
            bits.append("\u2318Z undo")
            self.status.config(text="  ·  ".join(bits))
        if self.current_file_path:
            self.path_lbl.config(text=self.current_file_path)
        else:
            self.path_lbl.config(text="")

    def _render_main(self):
        for w in self.main.winfo_children():
            w.destroy()
        if self.view_mode == 'month': self._render_month()
        elif self.view_mode == 'week': self._render_week()
        elif self.view_mode == 'day': self._render_day()
        elif self.view_mode == 'year': self._render_year()

    # =====================================================================
    # Month view
    # =====================================================================
    def _render_month(self):
        bar = tk.Frame(self.main, bg=PAPER)
        bar.pack(fill=tk.X, padx=32, pady=(20, 6))
        for i in range(7):
            bar.columnconfigure(i, weight=1, uniform='col')
        for i, name in enumerate(['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']):
            tk.Label(bar, text=letterspace(name, ' '),
                     font=(F_SANS, 8, 'bold'),
                     bg=PAPER, fg=INK_FAINT)\
                .grid(row=0, column=i, sticky='nsew', pady=4)

        wrap = tk.Frame(self.main, bg=RULE_FAINT)
        wrap.pack(fill=tk.BOTH, expand=True, padx=32, pady=(0, 20))
        for i in range(7):
            wrap.columnconfigure(i, weight=1, uniform='col')
        for i in range(6):
            wrap.rowconfigure(i, weight=1, uniform='row')

        today = datetime.now().date()
        first = date(self.view_year, self.view_month, 1)
        start = first - timedelta(days=first.weekday())

        cur = start
        for r in range(6):
            for c in range(7):
                d = cur
                in_month = (d.month == self.view_month and d.year == self.view_year)
                template = [e for e in self.events_for(d)
                            if self.matches_search(e)] if in_month else []
                dated = [e for e in self._dated_events_for(d)
                         if classify_event(e) in self.visible_calendars
                         and self.matches_search(e)] if in_month else []
                self._month_cell(wrap, r, c, d, in_month,
                                 d == today, d == self.selected_date,
                                 template, dated)
                cur += timedelta(days=1)

    def _month_cell(self, wrap, r, c, d, in_month, is_today, is_selected,
                    template_events, dated_events):
        if not in_month: bg = PAPER_ADJ
        elif is_today:   bg = ORBIT_WASH
        elif is_selected: bg = SELECT_CELL
        else: bg = PAPER_CARD

        cell = tk.Frame(wrap, bg=bg, cursor='hand2')
        cell.grid(row=r, column=c, sticky='nsew', padx=1, pady=1)

        top = tk.Frame(cell, bg=bg)
        top.pack(fill=tk.X, padx=6, pady=(6, 2))

        num = str(d.day)
        if in_month and is_today:
            cv = tk.Canvas(top, width=24, height=24, bg=bg,
                           highlightthickness=0, bd=0)
            cv.pack(side=tk.LEFT)
            cv.create_oval(0, 0, 24, 24, fill=ORBIT, outline='')
            cv.create_text(12, 13, text=num, fill='#ffffff',
                           font=(F_SERIF, 12, 'bold'))
        elif in_month and is_selected:
            cv = tk.Canvas(top, width=24, height=24, bg=bg,
                           highlightthickness=0, bd=0)
            cv.pack(side=tk.LEFT)
            cv.create_oval(0, 0, 24, 24, fill=SELECT_FILL, outline='')
            cv.create_text(12, 13, text=num, fill='#ffffff',
                           font=(F_SERIF, 12, 'bold'))
        else:
            tk.Label(top, text=num,
                     font=(F_SERIF, 12, 'bold' if in_month else 'normal'),
                     bg=bg, fg=INK if in_month else INK_FAINT)\
                .pack(side=tk.LEFT, padx=4)

        # Merge template + dated into a single sorted chip list
        chips = []

        for ev in template_events:
            chips.append({
                "time": ev.get("time", ""),
                "activity": ev.get("activity", ""),
                "color": color_of(classify_event(ev)),
                "id": ev.get("id"),
                "source": "template",
                "all_day": False,
            })

        for ev in dated_events:
            chips.append({
                "time": ev.get("time", ""),
                "activity": ev.get("activity", ""),
                "color": color_of(classify_event(ev)),
                "id": ev.get("id"),
                "source": "dated",
                "all_day": bool(ev.get("all_day", False)),
            })

        def _sort_key(ch):
            if ch["all_day"]:
                return (0, "")
            try:
                t = datetime.strptime(ch["time"], '%I:%M %p')
                return (1, t.strftime("%H:%M"))
            except Exception:
                return (1, "99:99")

        chips.sort(key=_sort_key)

        MAX_CHIPS = 3
        shown = chips[:MAX_CHIPS]

        if in_month and shown:
            tk.Frame(cell, bg=RULE_FAINT if not is_today else RULE, height=1)\
                .pack(fill=tk.X, padx=8, pady=(4, 4))

            for chip in shown:
                row = tk.Frame(cell, bg=bg, cursor='hand2')
                row.pack(fill=tk.X, padx=8, pady=1)

                tk.Frame(row, bg=chip["color"], width=2, height=10)\
                    .pack(side=tk.LEFT, padx=(0, 6))

                act = chip["activity"]
                if chip["all_day"]:
                    act = "• " + act

                completion = self._completion_for(
                    chip["id"], d.strftime("%Y-%m-%d"))

                prefix = ""
                text_color = INK
                if completion:
                    st = completion.get("status")
                    if st == "done":
                        prefix = "✓  "
                        text_color = "#7a8a7d"   # muted green-grey
                    elif st == "skipped":
                        prefix = "✗  "
                        text_color = INK_FAINT
                    elif st == "partial":
                        prefix = "◐  "
                        text_color = "#8a7d5a"

                label = prefix + act[:20] + ("\u2026" if len(act) > 20 else "")

                tk.Label(row, text=label,
                         font=(F_SANS, 9),
                         bg=bg, fg=text_color, anchor='w')\
                    .pack(side=tk.LEFT, fill='x', expand=True)

                def on_chip(event, dd=d, c=chip):
                    self._chip_menu(event, dd, c)
                    return "break"

                for w in (row,) + tuple(row.winfo_children()):
                    w.bind('<Button-1>', on_chip)

            if len(chips) > MAX_CHIPS:
                tk.Label(cell, text=f"+{len(chips)-MAX_CHIPS}",
                         font=(F_SANS, 8), bg=bg, fg=INK_FAINT, anchor='w')\
                    .pack(fill='x', padx=8, pady=(0, 2))

        def on_click(_e, dd=d):
            self.selected_date = dd
            self.selected_event = None
            self._render_all()
        cell.bind('<Button-1>', on_click)
        cell.bind('<Button-2>', lambda e, dd=d: self._right_click_empty(e, dd))
        cell.bind('<Button-3>', lambda e, dd=d: self._right_click_empty(e, dd))
        cell.bind('<Control-Button-1>', lambda e, dd=d: self._right_click_empty(e, dd))
        top.bind('<Button-1>', on_click)

    # =====================================================================
    # Week view
    # =====================================================================
    def _render_week(self):
        self.ROW_H = 46
        row_h = self.ROW_H
        start = self.selected_date - timedelta(days=self.selected_date.weekday())
        days = [start + timedelta(days=i) for i in range(7)]
        today = datetime.now().date()

        header = tk.Frame(self.main, bg=PAPER)
        header.pack(fill=tk.X, padx=32, pady=(20, 8))
        tk.Frame(header, bg=PAPER, width=64).grid(row=0, column=0)
        for i, d in enumerate(days):
            header.columnconfigure(i + 1, weight=1, uniform='wkcol')
            cell = tk.Frame(header, bg=PAPER)
            cell.grid(row=0, column=i + 1, sticky='nsew', padx=2, pady=2)
            tk.Label(cell,
                     text=letterspace(['MON', 'TUE', 'WED', 'THU',
                                        'FRI', 'SAT', 'SUN'][i], ' '),
                     font=(F_SANS, 8, 'bold'),
                     bg=PAPER, fg=INK_FAINT).pack()
            if d == today:
                cv = tk.Canvas(cell, width=28, height=28, bg=PAPER,
                               highlightthickness=0, bd=0)
                cv.pack(pady=(2, 0))
                cv.create_oval(1, 1, 27, 27, fill=ORBIT, outline='')
                cv.create_text(14, 15, text=str(d.day), fill='#ffffff',
                               font=(F_SERIF, 13, 'bold'))
            else:
                tk.Label(cell, text=str(d.day), font=(F_SERIF, 15),
                         bg=PAPER, fg=INK).pack(pady=4)

        body = tk.Frame(self.main, bg=PAPER)
        body.pack(fill=tk.BOTH, expand=True, padx=32, pady=(0, 20))
        hours = list(range(6, 23))

        gut = tk.Frame(body, bg=PAPER, width=64)
        gut.pack(side=tk.LEFT, fill=tk.Y)
        gut.pack_propagate(False)
        for h in hours:
            tk.Label(gut, text=f"{h:02d}:00", font=(F_MONO, 9),
                     bg=PAPER, fg=INK_FAINT, anchor='e')\
                .pack(fill=tk.X, pady=(row_h - 14, 0))

        wrap = tk.Frame(body, bg=RULE_FAINT)
        wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for i in range(7):
            wrap.columnconfigure(i, weight=1, uniform='wkcol')

        for i, d in enumerate(days):
            col = tk.Frame(wrap, bg=PAPER_CARD)
            col.grid(row=0, column=i, sticky='nsew', padx=1, pady=1)
            for h in hours:
                hr = tk.Frame(col, bg=PAPER_CARD, height=row_h)
                hr.pack(fill=tk.X)
                hr.pack_propagate(False)
                tk.Frame(hr, bg=RULE_FAINT, height=1)\
                    .pack(fill=tk.X, side=tk.BOTTOM)
                hr.bind('<Button-1>',
                        lambda e, dd=d, hh=h: self._drag_start(e, dd, hh))
                hr.bind('<B1-Motion>', self._drag_motion)
                hr.bind('<ButtonRelease-1>', self._drag_end)
                hr.bind('<Button-2>',
                        lambda e, dd=d, hh=h: self._right_click_empty(e, dd, hh))
                hr.bind('<Button-3>',
                        lambda e, dd=d, hh=h: self._right_click_empty(e, dd, hh))

            # Template events
            events = [e for e in self.events_for(d) if self.matches_search(e)]
            for ev in events:
                self._place_event_block(col, d, ev, row_h, single_line=True)

            # Dated events (LMS classes at their exact times)
            for ev in self._dated_events_for(d):
                if ev.get("all_day"):
                    continue
                if classify_event(ev) not in self.visible_calendars:
                    continue
                if not self.matches_search(ev):
                    continue
                self._place_dated_block(col, d, ev, row_h)

    # =====================================================================
    # Day view
    # =====================================================================
    def _render_day(self):
        self.ROW_H = 54
        row_h = self.ROW_H
        d = self.selected_date

        hdr = tk.Frame(self.main, bg=PAPER)
        hdr.pack(fill=tk.X, padx=32, pady=(24, 12))
        tk.Label(hdr, text=letterspace(d.strftime('%A').upper(), ' '),
                 font=(F_SANS, 9, 'bold'),
                 bg=PAPER, fg=ORBIT).pack(anchor='w')
        big = tk.Frame(hdr, bg=PAPER)
        big.pack(anchor='w', pady=(4, 0))
        tk.Label(big, text=str(d.day), font=(F_SERIF, 42, 'bold'),
                 bg=PAPER, fg=INK).pack(side=tk.LEFT)
        tk.Label(big, text=d.strftime('%B %Y').upper(),
                 font=(F_SANS, 11, 'bold'),
                 bg=PAPER, fg=INK_FAINT)\
            .pack(side=tk.LEFT, padx=(16, 0), pady=(16, 0))
        rule_row = tk.Frame(hdr, bg=PAPER)
        rule_row.pack(fill=tk.X, pady=(14, 0))
        tk.Frame(rule_row, bg=ORBIT, height=2, width=48).pack(side=tk.LEFT)
        tk.Frame(rule_row, bg=RULE, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # All-day assignments strip (above the timeline)
        all_day_items = [e for e in self._dated_events_for(d)
                         if e.get("all_day")
                         and classify_event(e) in self.visible_calendars]
        if all_day_items:
            strip = tk.Frame(self.main, bg=PAPER)
            strip.pack(fill=tk.X, padx=32, pady=(0, 4))
            tk.Label(strip, text=letterspace("DUE TODAY"),
                     font=(F_SANS, 8, 'bold'),
                     bg=PAPER, fg=INK_FAINT).pack(anchor='w', pady=(0, 4))
            for ev in all_day_items:
                row = tk.Frame(strip, bg=PAPER_CARD,
                               highlightthickness=1,
                               highlightbackground=RULE_FAINT,
                               cursor='hand2')
                row.pack(fill=tk.X, pady=2)
                inner = tk.Frame(row, bg=PAPER_CARD)
                inner.pack(fill=tk.X, padx=12, pady=8)
                color = color_of(classify_event(ev))
                tk.Frame(inner, bg=color, width=3, height=16)\
                    .pack(side=tk.LEFT, padx=(0, 10))
                tk.Label(inner, text=ev.get("activity", ""),
                         font=(F_SERIF, 12), bg=PAPER_CARD, fg=INK,
                         anchor='w')\
                    .pack(side=tk.LEFT, fill='x', expand=True)

                def on_click(event, dd=d, e=ev):
                    chip = {
                        "id": e.get("id"),
                        "activity": e.get("activity", ""),
                        "source": "dated",
                        "duration_min": e.get("duration_min"),
                    }
                    self._chip_menu(event, dd, chip)
                    return "break"

                for w in (row, inner) + tuple(inner.winfo_children()):
                    w.bind('<Button-1>', on_click)

        body = tk.Frame(self.main, bg=PAPER)
        body.pack(fill=tk.BOTH, expand=True, padx=32, pady=(16, 20))
        hours = list(range(6, 23))

        gut = tk.Frame(body, bg=PAPER, width=64)
        gut.pack(side=tk.LEFT, fill=tk.Y)
        gut.pack_propagate(False)
        for h in hours:
            tk.Label(gut, text=f"{h:02d}:00", font=(F_MONO, 9),
                     bg=PAPER, fg=INK_FAINT, anchor='e')\
                .pack(fill=tk.X, pady=(row_h - 14, 0))

        timeline = tk.Frame(body, bg=RULE_FAINT)
        timeline.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        col = tk.Frame(timeline, bg=PAPER_CARD)
        col.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        for h in hours:
            hr = tk.Frame(col, bg=PAPER_CARD, height=row_h)
            hr.pack(fill=tk.X)
            hr.pack_propagate(False)
            tk.Frame(hr, bg=RULE_FAINT, height=1)\
                .pack(fill=tk.X, side=tk.BOTTOM)
            hr.bind('<Button-1>',
                    lambda e, dd=d, hh=h: self._drag_start(e, dd, hh))
            hr.bind('<B1-Motion>', self._drag_motion)
            hr.bind('<ButtonRelease-1>', self._drag_end)
            hr.bind('<Button-2>',
                    lambda e, dd=d, hh=h: self._right_click_empty(e, dd, hh))
            hr.bind('<Button-3>',
                    lambda e, dd=d, hh=h: self._right_click_empty(e, dd, hh))

        events = [e for e in self.events_for(d) if self.matches_search(e)]
        for ev in events:
            self._place_event_block(col, d, ev, row_h, single_line=False)

        # Dated (LMS) events for this exact day
        for ev in self._dated_events_for(d):
            if ev.get("all_day"):
                continue
            if classify_event(ev) not in self.visible_calendars:
                continue
            if not self.matches_search(ev):
                continue
            self._place_dated_block(col, d, ev, row_h)

    def _place_event_block(self, col, d, ev, row_h, single_line):
        act = ev.get('activity', '')
        color = color_of(classify_event(ev))
        hh, mn = parse_time(ev.get('time', '9:00 AM'))
        if hh < 6 or hh > 22: return
        y = (hh - 6) * row_h + int(mn / 60 * row_h)
        block_h = 30 if single_line else 44

        block = tk.Frame(col, bg=color, cursor='hand2')
        block.place(x=4, y=y, relwidth=1.0, width=-10, height=block_h)
        tk.Frame(block, bg='#ffffff', width=2)\
            .pack(side=tk.LEFT, fill=tk.Y, padx=(4, 0))
        wrap = tk.Frame(block, bg=color)
        wrap.pack(side=tk.LEFT, fill='both', expand=True, padx=(6, 4))

        if single_line:
            tk.Label(wrap, text=act, font=(F_SANS, 9, 'bold'),
                     bg=color, fg='#ffffff', anchor='w')\
                .pack(fill='x', pady=6)
        else:
            tk.Label(wrap, text=ev.get('time', ''), font=(F_MONO, 9),
                     bg=color, fg='#ffffff', anchor='w')\
                .pack(fill='x', pady=(4, 0))
            tk.Label(wrap, text=act, font=(F_SERIF, 12),
                     bg=color, fg='#ffffff', anchor='w')\
                .pack(fill='x')

        def on_click(event):
            chip = {
                "id": ev.get("id"),
                "activity": ev.get("activity", ""),
                "source": "template",
                "duration_min": ev.get("duration_min"),
            }
            self._chip_menu(event, d, chip)
            return "break"
        def rec(w):
            w.bind('<Button-1>', on_click)
            for ch in w.winfo_children():
                rec(ch)
        rec(block)

    def _place_dated_block(self, col, d, ev, row_h):
        """Render a dated event (LMS class) on the timeline."""
        act = ev.get("activity", "")
        color = color_of(classify_event(ev))
        hh, mn = parse_time(ev.get("time", "9:00 AM"))
        if hh < 6 or hh > 22:
            return
        y = (hh - 6) * row_h + int(mn / 60 * row_h)
        block_h = 30

        block = tk.Frame(col, bg=color, cursor='hand2')
        block.place(x=2, y=y, relwidth=1.0, width=-6, height=block_h)

        tk.Frame(block, bg='#ffffff', width=2)\
            .pack(side=tk.LEFT, fill=tk.Y, padx=(4, 0))

        wrap = tk.Frame(block, bg=color)
        wrap.pack(side=tk.LEFT, fill='both', expand=True, padx=(6, 4))

        tk.Label(wrap, text=act, font=(F_SANS, 9, 'bold'),
                 bg=color, fg='#ffffff', anchor='w')\
            .pack(fill='x', pady=6)

        def on_click(event):
            chip = {
                "id": ev.get("id"),
                "activity": ev.get("activity", ""),
                "source": "dated",
                "duration_min": ev.get("duration_min"),
            }
            self._chip_menu(event, d, chip)
            return "break"

        def rec(w):
            w.bind('<Button-1>', on_click)
            for ch in w.winfo_children():
                rec(ch)
        rec(block)

    # =====================================================================
    # Drag-to-create
    # =====================================================================
    def _drag_start(self, event, d, hour):
        if event.num != 1: return
        row_h = self.ROW_H
        hour_offset = (hour - 6) * row_h
        start_y = hour_offset + event.y
        col = event.widget.master
        self._drag = {
            'day': d, 'col': col, 'row_h': row_h,
            'hour_offset': hour_offset, 'start_y': start_y,
        }
        preview = tk.Frame(col, bg=ORBIT_WASH,
                           highlightthickness=1, highlightbackground=ORBIT)
        preview.place(x=4, y=start_y, relwidth=1.0, width=-10, height=row_h // 4)
        self._drag['preview'] = preview

    def _drag_motion(self, event):
        d = self._drag
        if not d: return
        current_y = d['hour_offset'] + event.y
        y0, y1 = min(d['start_y'], current_y), max(d['start_y'], current_y)
        h = max(d['row_h'] // 4, y1 - y0)
        if d.get('preview'):
            d['preview'].place(x=4, y=y0, relwidth=1.0, width=-10, height=h)

    def _drag_end(self, event):
        d = self._drag
        if not d: return
        current_y = d['hour_offset'] + event.y
        y0, y1 = min(d['start_y'], current_y), max(d['start_y'], current_y)
        if d.get('preview'): d['preview'].destroy()
        day = d['day']
        row_h = d['row_h']
        self._drag = None

        if abs(y1 - y0) < 6:
            self.selected_date = day
            self.selected_event = None
            self._render_all()
            return

        hour = 6 + int(y0 // row_h)
        minute = int((y0 % row_h) / row_h * 60)
        minute = (minute // 15) * 15
        if minute >= 60: minute = 45; hour += 1
        if hour < 6 or hour > 23: return
        duration = max(15, int((y1 - y0) / row_h * 60))
        duration = (duration // 15) * 15
        self._add_event(weekday_of(day), hour, minute, duration_min=duration)

    # =====================================================================
    # Year view
    # =====================================================================
    def _render_year(self):
        wrap = tk.Frame(self.main, bg=PAPER)
        wrap.pack(fill=tk.BOTH, expand=True, padx=32, pady=24)
        for i in range(4): wrap.columnconfigure(i, weight=1, uniform='yr')
        for i in range(3): wrap.rowconfigure(i, weight=1, uniform='yr')
        today = datetime.now().date()
        for m in range(1, 13):
            r, c = divmod(m - 1, 4)
            self._mini_month(wrap, m, r, c, today)

    def _mini_month(self, parent, month, r, c, today):
        card = tk.Frame(parent, bg=PAPER, highlightthickness=1,
                        highlightbackground=RULE_FAINT)
        card.grid(row=r, column=c, sticky='nsew', padx=6, pady=6)
        inner_card = tk.Frame(card, bg=PAPER)
        inner_card.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)
        tk.Label(inner_card, text=pycal.month_name[month],
                 font=(F_SERIF, 13, 'bold'),
                 bg=PAPER, fg=INK).pack(anchor='w', pady=(0, 6))
        tk.Frame(inner_card, bg=ORBIT, height=2, width=24)\
            .pack(anchor='w', pady=(0, 8))
        inner = tk.Frame(inner_card, bg=PAPER)
        inner.pack(fill=tk.BOTH, expand=True)
        for i in range(7): inner.columnconfigure(i, weight=1, uniform='ymm')
        for i, name in enumerate(['M', 'T', 'W', 'T', 'F', 'S', 'S']):
            tk.Label(inner, text=name, font=(F_SANS, 7, 'bold'),
                     bg=PAPER, fg=INK_FAINT)\
                .grid(row=0, column=i, sticky='nsew')
        pycal.setfirstweekday(pycal.MONDAY)
        matrix = pycal.monthcalendar(self.view_year, month)
        for rr, week in enumerate(matrix):
            for cc, dn in enumerate(week):
                if dn == 0: continue
                d = date(self.view_year, month, dn)
                is_today = (d == today)
                has_ev = (len(self.events_for(d)) > 0 or
                          len(self._dated_events_for(d)) > 0)
                if is_today: bg, fg = ORBIT, '#ffffff'
                else: bg = PAPER; fg = ORBIT if has_ev else INK
                cell = tk.Label(inner, text=str(dn),
                                font=(F_SERIF, 9,
                                      'bold' if (is_today or has_ev) else 'normal'),
                                bg=bg, fg=fg, cursor='hand2', width=2, pady=1)
                cell.grid(row=rr + 1, column=cc, sticky='nsew')
                cell.bind('<Button-1>', lambda e, dd=d: self._year_pick(dd))

    def _year_pick(self, d):
        self.selected_date = d
        self.view_year = d.year
        self.view_month = d.month
        self.view_mode = 'month'
        self._render_all()

    # =====================================================================
    def run(self):
        self.root.mainloop()


def main():
    root = tk.Tk()
    initial = sys.argv[1] if len(sys.argv) > 1 else None
    CalendarApp(root, initial_path=initial)

    root.update_idletasks()
    bring_to_front(root)
    root.after(300, lambda: bring_to_front(root))

    root.mainloop()


if __name__ == "__main__":
    main()