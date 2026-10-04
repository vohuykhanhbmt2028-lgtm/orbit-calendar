import tkinter as tk
from datetime import datetime

from config import DAYS_FULL
from ui_helpers import AnimatedButton


BRAND_RED  = '#b01b1b'
BRAND_DEEP = '#7d1212'


_EVENT_STYLES = [
    (['class', 'lecture', 'seminar', 'math', 'bio', 'chem',
      'physics', 'japanese', 'english', 'history', 'econ', 'lab'],
     '#e8f0fe', '#1a73e8'),
    (['gym', 'exercise', 'run', 'workout', 'yoga', 'sport', 'train'],
     '#e6f4ea', '#137333'),
    (['work', 'job', 'shift'],
     '#fef7e0', '#b06000'),
    (['study', 'read', 'homework', 'exam', 'review'],
     '#fce8e6', '#c5221f'),
    (['meeting', 'call', 'appointment', 'therapy'],
     '#f3e8fd', '#8430ce'),
    (['breakfast', 'lunch', 'dinner', 'meal', 'eat', 'coffee'],
     '#fef7e0', '#b06000'),
    (['sleep', 'rest', 'wind', 'free', 'break'],
     '#f1f3f4', '#5f6368'),
]


def _classify(text):
    t = text.lower()
    for kws, bg, accent in _EVENT_STYLES:
        if any(k in t for k in kws):
            return bg, accent
    return '#fbe9e9', '#b01b1b'


class CalendarView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg='#ffffff')
        self.app = app

        # ---- Header ----
        header = tk.Frame(self, bg='#ffffff')
        header.pack(fill=tk.X, padx=40, pady=(30, 18))

        top = tk.Frame(header, bg='#ffffff')
        top.pack(fill=tk.X)

        tk.Label(top, text=' '.join("PREVIEW"),
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg='#b01b1b').pack(side=tk.LEFT)

        self.variant_lbl = tk.Label(top, text="",
                                     font=('Helvetica', 9, 'bold'),
                                     bg='#ffffff', fg='#cccccc')
        self.variant_lbl.pack(side=tk.RIGHT)

        tk.Label(header, text="Here's your plan",
                 font=('Helvetica Neue', 28, 'bold'),
                 bg='#ffffff', fg='#1a1a1a').pack(anchor='w', pady=(12, 0))

        self.sub_lbl = tk.Label(
            header,
            text="Happy with this? Commit it, or try another variant.",
            font=('Helvetica', 13),
            bg='#ffffff', fg='#888')
        self.sub_lbl.pack(anchor='w', pady=(8, 0))

        # ---- Grid area ----
        self.container = tk.Frame(self, bg='#ffffff')
        self.container.pack(fill=tk.BOTH, expand=True, padx=40, pady=(12, 90))

        self.placeholder = tk.Label(
            self.container,
            text="No schedule yet.",
            font=('Helvetica', 12), bg='#ffffff', fg='#999')
        self.placeholder.pack(expand=True)

        # ---- Floating buttons ----
        # Primary: commit to editor (dark, prominent)
        self.float_commit = AnimatedButton(
            self, text="Use this  \u2192",
            command=self._commit,
            bg='#1a1a1a', hover_bg='#000000', active_bg='#333333',
            fg='#ffffff',
            font=('Helvetica Neue', 12, 'bold'),
            pad_x=26, pad_y=13)
        self.float_commit.place(relx=1.0, rely=1.0,
                                 anchor='se', x=-30, y=-30)

        # Secondary: back to variants
        self.float_back = AnimatedButton(
            self, text="\u2190  Choose another",
            command=self._back_to_variants,
            bg='#ffffff', hover_bg='#f4f4f4', active_bg='#e8e8e8',
            fg='#1a1a1a',
            font=('Helvetica Neue', 11, 'bold'),
            pad_x=20, pad_y=12)
        self.float_back.place(relx=1.0, rely=1.0,
                               anchor='se', x=-30, y=-84)

    # -------------------------------------------------------------
    def display(self, schedule, variant_name=None):
        for w in self.container.winfo_children():
            w.destroy()

        if variant_name:
            self.variant_lbl.config(text=variant_name.upper())
        else:
            self.variant_lbl.config(text="")

        all_times = set()
        for day in DAYS_FULL:
            for ev in schedule.get(day, []):
                all_times.add(ev.get('time', ''))
        all_times.discard('')

        def tkey(t):
            try:
                return datetime.strptime(t, '%I:%M %p')
            except Exception:
                return datetime.min

        time_slots = sorted(all_times, key=tkey)

        if not time_slots:
            tk.Label(self.container, text="No events scheduled.",
                     font=('Helvetica', 14),
                     bg='#ffffff', fg='#666').pack(expand=True)
            return

        grid = tk.Frame(self.container, bg='#ffffff')
        grid.pack(fill=tk.BOTH, expand=True)

        TIME_COL_W = 72
        corner = tk.Frame(grid, bg='#ffffff',
                          width=TIME_COL_W, height=48)
        corner.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        corner.grid_propagate(False)

        for i, day in enumerate(DAYS_FULL, start=1):
            h = tk.Frame(grid, bg='#ffffff')
            h.grid(row=0, column=i, sticky='nsew', padx=3, pady=(0, 12))
            tk.Label(h, text=day[:3].upper(),
                     font=('Helvetica', 9, 'bold'),
                     bg='#ffffff', fg='#999').pack()
            tk.Label(h, text=day,
                     font=('Helvetica Neue', 13, 'bold'),
                     bg='#ffffff', fg='#1a1a1a').pack(pady=(2, 0))

        for row_idx, time_slot in enumerate(time_slots, start=1):
            tl = tk.Label(grid, text=time_slot,
                          font=('Helvetica Neue', 10),
                          bg='#ffffff', fg='#999', anchor='e')
            tl.grid(row=row_idx, column=0, sticky='ne',
                    padx=(0, 12), pady=(14, 14))

            for col_idx, day in enumerate(DAYS_FULL, start=1):
                ev = None
                for e in schedule.get(day, []):
                    if e.get('time') == time_slot:
                        ev = e
                        break

                if ev:
                    self._event_block(grid, ev, row_idx, col_idx)
                else:
                    tk.Frame(grid, bg='#f7f7f7', height=48)\
                        .grid(row=row_idx, column=col_idx,
                              sticky='nsew', padx=3, pady=3)

        grid.columnconfigure(0, minsize=TIME_COL_W, weight=0)
        for i in range(1, 8):
            grid.columnconfigure(i, weight=1, minsize=110)

        for r in range(len(time_slots) + 1):
            if r == 0:
                grid.rowconfigure(r, weight=0, minsize=48)
            else:
                grid.rowconfigure(r, weight=0, minsize=64)

    # -------------------------------------------------------------
    def _event_block(self, parent, event, row, col):
        activity = event.get('activity', '')
        time_str = event.get('time', '')
        bg, accent = _classify(activity)

        wrapper = tk.Frame(parent, bg='#ffffff')
        wrapper.grid(row=row, column=col, sticky='nsew', padx=3, pady=3)

        block = tk.Frame(wrapper, bg=bg,
                         highlightthickness=1,
                         highlightbackground=accent, bd=0)
        block.pack(fill=tk.BOTH, expand=True)

        bar = tk.Frame(block, bg=accent, width=4)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        bar.pack_propagate(False)

        content = tk.Frame(block, bg=bg)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                     padx=10, pady=8)

        tk.Label(content, text=time_str,
                 font=('Helvetica Neue', 9, 'bold'),
                 bg=bg, fg=accent, anchor='w')\
            .pack(anchor='w', fill='x')

        tk.Label(content, text=activity,
                 font=('Helvetica Neue', 11),
                 bg=bg, fg='#202124',
                 anchor='w', justify='left', wraplength=140)\
            .pack(anchor='w', fill='x', pady=(2, 0))

    # -------------------------------------------------------------
    # Button actions
    # -------------------------------------------------------------
    def _commit(self):
        """Save the current schedule to a new file and open the editor."""
        if not getattr(self.app, 'current_schedule', None):
            from tkinter import messagebox
            messagebox.showwarning("No Schedule", "Nothing to commit.")
            return
        self.app.commit_to_editor()

    def _back_to_variants(self):
        """Go back to the variant picker without committing."""
        self.app.show_variants()