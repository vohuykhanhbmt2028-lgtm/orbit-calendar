"""Home view — the launcher, in the spirit of Word's start screen."""

import os
import tkinter as tk

from ui_helpers import AnimatedButton
import documents


PAPER       = '#faf8f5'
PAPER_CARD  = '#ffffff'
INK         = '#1a1715'
INK_SOFT    = '#6e6559'
INK_FAINT   = '#a59c8e'
RULE        = '#e6e1d6'
RULE_FAINT  = '#eeeae1'
ORBIT       = '#b01b1b'
ORBIT_DEEP  = '#7d1212'

F_SERIF = 'Georgia'
F_SANS  = 'Helvetica Neue'
F_MONO  = 'Courier New'


def letterspace(s, gap=' '):
    return gap.join(list(s))


class HomeView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAPER)
        self.app = app

    def refresh(self):
        for w in self.winfo_children():
            w.destroy()
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        outer = tk.Frame(self, bg=PAPER)
        outer.pack(fill=tk.BOTH, expand=True, padx=64, pady=(52, 44))

        # ---- Header ----
        header = tk.Frame(outer, bg=PAPER)
        header.pack(fill=tk.X, pady=(0, 42))

        tk.Label(header, text=letterspace("ORBIT", ' '),
                 font=(F_SANS, 11, 'bold'),
                 bg=PAPER, fg=ORBIT).pack(anchor='w')

        tk.Label(header, text="A quiet place to plan your week.",
                 font=(F_SERIF, 32, 'bold'),
                 bg=PAPER, fg=INK).pack(anchor='w', pady=(12, 0))

        tk.Label(header,
                 text="Create a new calendar, or open one you've made before.",
                 font=(F_SANS, 13),
                 bg=PAPER, fg=INK_SOFT).pack(anchor='w', pady=(8, 0))

        # ---- Two columns ----
        cols = tk.Frame(outer, bg=PAPER)
        cols.pack(fill=tk.BOTH, expand=True)

        # Left: recents
        left = tk.Frame(cols, bg=PAPER)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 40))

        tk.Label(left, text=letterspace("RECENT"),
                 font=(F_SANS, 9, 'bold'),
                 bg=PAPER, fg=INK_FAINT).pack(anchor='w', pady=(0, 14))

        recents = documents.get_recents()
        if not recents:
            self._empty_state(left)
        else:
            for entry in recents:
                self._recent_row(left, entry)

        # Right: actions
        right = tk.Frame(cols, bg=PAPER, width=340)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        tk.Label(right, text=letterspace("START"),
                 font=(F_SANS, 9, 'bold'),
                 bg=PAPER, fg=INK_FAINT).pack(anchor='w', pady=(0, 14))

        self._new_card(right)
        self._open_link(right)

    # ------------------------------------------------------------------
    def _empty_state(self, parent):
        card = tk.Frame(parent, bg=PAPER_CARD,
                         highlightthickness=1,
                         highlightbackground=RULE_FAINT)
        card.pack(fill=tk.X)
        inner = tk.Frame(card, bg=PAPER_CARD)
        inner.pack(padx=32, pady=44)

        tk.Label(inner, text="No calendars yet.",
                 font=(F_SERIF, 15, 'bold'),
                 bg=PAPER_CARD, fg=INK).pack()
        tk.Label(inner, text="Your recent files will appear here.",
                 font=(F_SANS, 11),
                 bg=PAPER_CARD, fg=INK_FAINT).pack(pady=(6, 0))

    def _recent_row(self, parent, entry):
        name = entry.get('name', 'Untitled')
        path = entry.get('path', '')
        count, variant = documents.summarize(path)

        row = tk.Frame(parent, bg=PAPER_CARD,
                        highlightthickness=1,
                        highlightbackground=RULE_FAINT,
                        cursor='hand2')
        row.pack(fill=tk.X, pady=(0, 8))

        inner = tk.Frame(row, bg=PAPER_CARD)
        inner.pack(fill=tk.X, padx=22, pady=18)

        tk.Label(inner, text=name,
                 font=(F_SERIF, 15, 'bold'),
                 bg=PAPER_CARD, fg=INK, anchor='w').pack(anchor='w')

        meta_bits = []
        if count:
            meta_bits.append(f"{count} events")
        if variant:
            meta_bits.append(variant)
        meta = "  ·  ".join(meta_bits) if meta_bits else "Empty calendar"

        tk.Label(inner, text=meta,
                 font=(F_SANS, 10),
                 bg=PAPER_CARD, fg=INK_FAINT, anchor='w')\
            .pack(anchor='w', pady=(3, 0))

        tk.Label(inner, text=self._short_path(path),
                 font=(F_MONO, 8),
                 bg=PAPER_CARD, fg='#cfc7b9', anchor='w')\
            .pack(anchor='w', pady=(8, 0))

        def on_click(_e):  self.app.open_document(path)
        def on_right(_e):  self._recent_context(path)

        def rec(w):
            w.bind('<Button-1>', on_click)
            w.bind('<Button-2>', on_right)
            w.bind('<Button-3>', on_right)
            w.bind('<Control-Button-1>', on_right)
            for ch in w.winfo_children():
                rec(ch)
        rec(row)

        def hover_on(_):
            row.config(highlightbackground=RULE)
            self._set_bg(row, '#fdfbf8')
        def hover_off(_):
            row.config(highlightbackground=RULE_FAINT)
            self._set_bg(row, PAPER_CARD)

        row.bind('<Enter>', hover_on)
        row.bind('<Leave>', hover_off)

    @staticmethod
    def _set_bg(widget, color):
        try:
            widget.config(bg=color)
        except Exception:
            pass
        for ch in widget.winfo_children():
            HomeView._set_bg(ch, color)

    def _recent_context(self, path):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Open",
                          command=lambda: self.app.open_document(path))
        menu.add_separator()
        menu.add_command(label="Remove from Recents",
                          command=lambda: self._remove_recent(path))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def _remove_recent(self, path):
        documents.remove_from_recents(path)
        self.refresh()

    def _short_path(self, path):
        home = os.path.expanduser('~')
        return '~' + path[len(home):] if path.startswith(home) else path

    # ------------------------------------------------------------------
    def _new_card(self, parent):
        card = tk.Frame(parent, bg=PAPER_CARD,
                         highlightthickness=1,
                         highlightbackground=RULE,
                         cursor='hand2')
        card.pack(fill=tk.X)

        inner = tk.Frame(card, bg=PAPER_CARD)
        inner.pack(fill=tk.X, padx=30, pady=30)

        tk.Label(inner, text="+",
                 font=(F_SERIF, 34, 'bold'),
                 bg=PAPER_CARD, fg=ORBIT).pack(anchor='w')

        tk.Label(inner, text="New Calendar",
                 font=(F_SERIF, 19, 'bold'),
                 bg=PAPER_CARD, fg=INK).pack(anchor='w', pady=(14, 0))

        tk.Label(inner,
                 text="Start with a blank week.\nWe'll ask a few questions.",
                 font=(F_SANS, 11),
                 bg=PAPER_CARD, fg=INK_SOFT,
                 justify='left').pack(anchor='w', pady=(8, 0))

        def on_click(_e): self.app.new_document()

        def rec_bind(w):
            w.bind('<Button-1>', on_click)
            for ch in w.winfo_children():
                rec_bind(ch)
        rec_bind(card)

        def hover_on(_):
            card.config(highlightbackground=ORBIT)
            self._set_bg(card, '#fdfbf8')
        def hover_off(_):
            card.config(highlightbackground=RULE)
            self._set_bg(card, PAPER_CARD)

        card.bind('<Enter>', hover_on)
        card.bind('<Leave>', hover_off)

    def _open_link(self, parent):
        lbl = tk.Label(parent, text="Open File…",
                       font=(F_SANS, 11, 'underline'),
                       bg=PAPER, fg=ORBIT, cursor='hand2')
        lbl.pack(anchor='w', pady=(20, 0))
        lbl.bind('<Button-1>', lambda e: self.app.open_file())
        lbl.bind('<Enter>', lambda e: lbl.config(fg=ORBIT_DEEP))
        lbl.bind('<Leave>', lambda e: lbl.config(fg=ORBIT))