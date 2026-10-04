# Reusable UI builders.

import tkinter as tk
from tkinter import ttk

from config import DAYS_SHORT


# ---------------------------------------------------------------------------
# Sections / cards
# ---------------------------------------------------------------------------
def section(parent, title):
    frame = tk.LabelFrame(parent, text=title,
                          font=('Helvetica', 12, 'bold'),
                          bg='#fafafa', fg='#1a1a1a',
                          padx=14, pady=12, bd=1, relief='solid')
    frame.pack(fill='x', pady=8, padx=4)
    return frame


def form_card(parent, title, subtitle=None):
    """A card-style section with a header. Returns (card, body) so callers
    can pack content into `body`."""
    card = tk.Frame(parent, bg='#ffffff',
                    highlightthickness=1,
                    highlightbackground='#ececec',
                    bd=0)
    card.pack(fill='x', pady=(0, 16))

    header = tk.Frame(card, bg='#ffffff')
    header.pack(fill='x', padx=24, pady=(22, 14))

    tk.Label(header, text=title,
             font=('Helvetica Neue', 16, 'bold'),
             bg='#ffffff', fg='#1a1a1a', anchor='w')\
        .pack(anchor='w')

    if subtitle:
        tk.Label(header, text=subtitle,
                 font=('Helvetica', 11),
                 bg='#ffffff', fg='#8a8a8a', anchor='w')\
            .pack(anchor='w', pady=(2, 0))

    body = tk.Frame(card, bg='#ffffff')
    body.pack(fill='x', padx=24, pady=(0, 22))
    return card, body


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------
def field_label(parent, text):
    tk.Label(parent, text=text,
             font=('Helvetica', 10, 'bold'),
             bg='#ffffff', fg='#666', anchor='w')\
        .pack(anchor='w', pady=(0, 4))


def clean_entry(parent, var, width=30):
    return tk.Entry(parent, textvariable=var, font=('Helvetica', 12),
                    width=width, relief='flat',
                    bg='#f7f7f7', fg='#1a1a1a',
                    highlightthickness=1,
                    highlightbackground='#e4e4e4',
                    highlightcolor='#b01b1b',
                    insertbackground='#1a1a1a')


def clean_combo(parent, var, options, width=14):
    return ttk.Combobox(parent, textvariable=var, values=options,
                        state='readonly', width=width,
                        font=('Helvetica', 11))


def combo_row(parent, label, options, default):
    row = tk.Frame(parent, bg='#fafafa')
    row.pack(fill='x', pady=4)
    tk.Label(row, text=label, font=('Helvetica', 10),
             bg='#fafafa', fg='#555', width=14, anchor='w').pack(side=tk.LEFT)
    var = tk.StringVar(value=default)
    ttk.Combobox(row, textvariable=var, values=options,
                 state='readonly', width=18).pack(side=tk.LEFT)
    return var


# ---------------------------------------------------------------------------
# Day toggle
# ---------------------------------------------------------------------------
def day_pills(parent, initial=None):
    """Return a Frame with 7 big pill toggles. Access `holder._state`."""
    initial = initial or set()
    holder = tk.Frame(parent, bg='#ffffff')
    state = set(initial)
    buttons = {}
    labels = [('M', 'Mon'), ('Tu', 'Tue'), ('W', 'Wed'),
              ('Th', 'Thu'), ('F', 'Fri'), ('Sa', 'Sat'), ('Su', 'Sun')]

    for short, label in labels:
        selected = short in state
        bg = '#1a1a1a' if selected else '#ffffff'
        fg = '#ffffff' if selected else '#333333'
        border = '#1a1a1a' if selected else '#e0e0e0'

        b = tk.Label(holder, text=label,
                     font=('Helvetica Neue', 10, 'bold'),
                     bg=bg, fg=fg,
                     padx=14, pady=8,
                     cursor='hand2',
                     highlightthickness=1,
                     highlightbackground=border,
                     highlightcolor=border)
        b.pack(side=tk.LEFT, padx=(0, 6))
        buttons[short] = b

        def make_toggle(day, btn, st):
            def toggle(_event):
                if day in st:
                    st.remove(day)
                    btn.config(bg='#ffffff', fg='#333333',
                               highlightbackground='#e0e0e0',
                               highlightcolor='#e0e0e0')
                else:
                    st.add(day)
                    btn.config(bg='#1a1a1a', fg='#ffffff',
                               highlightbackground='#1a1a1a',
                               highlightcolor='#1a1a1a')
            return toggle

        b.bind('<Button-1>', make_toggle(short, b, state))

    holder._state = state
    holder._buttons = buttons
    return holder


def add_another_tile(parent, text, command):
    """A subtle dashed-look tile used as '+ Add another'."""
    tile = tk.Frame(parent, bg='#fafafa', cursor='hand2',
                    highlightthickness=1,
                    highlightbackground='#e0e0e0',
                    highlightcolor='#b01b1b')
    tile.pack(fill='x', pady=(4, 0))

    lbl = tk.Label(tile, text="+   " + text,
                   font=('Helvetica Neue', 11, 'bold'),
                   bg='#fafafa', fg='#888',
                   padx=16, pady=12, anchor='w')
    lbl.pack(fill='x')

    def enter(_):
        tile.config(bg='#f4f4f4')
        lbl.config(bg='#f4f4f4', fg='#1a1a1a')

    def leave(_):
        tile.config(bg='#fafafa')
        lbl.config(bg='#fafafa', fg='#888')

    for w in (tile, lbl):
        w.bind('<Button-1>', lambda e: command())
        w.bind('<Enter>', enter)
        w.bind('<Leave>', leave)
    return tile


# ---------------------------------------------------------------------------
# Small text-link button
# ---------------------------------------------------------------------------
def small_link_button(parent, text, command,
                       fg='#b01b1b', hover_fg='#7d1212',
                       bg='#ffffff',
                       font=('Helvetica', 10)):
    """A tiny flat text button that doesn't trigger macOS NSButton warnings."""
    lbl = tk.Label(parent, text=text, font=font,
                   bg=bg, fg=fg, cursor='hand2',
                   padx=4, pady=0)

    lbl.bind('<Enter>', lambda e: lbl.config(fg=hover_fg))
    lbl.bind('<Leave>', lambda e: lbl.config(fg=fg))
    lbl.bind('<Button-1>', lambda e: command())
    return lbl


# ---------------------------------------------------------------------------
# Icons
# ---------------------------------------------------------------------------
def render_icon_inline(parent, name, size=28):
    """Small inline icon for use inside section headers."""
    import icons
    c = tk.Canvas(parent, width=size, height=size,
                  bg=parent.cget('bg'), highlightthickness=0, bd=0)
    icons.render(c, name, size, bg=parent.cget('bg'))
    return c


# ---------------------------------------------------------------------------
# Event color classifier (used by older calendar variants)
# ---------------------------------------------------------------------------
def get_event_color(text):
    t = text.lower()
    if any(k in t for k in ['class', 'lecture', 'seminar', 'math', 'bio', 'chem', 'physics']):
        return '#e3f2fd'
    if any(k in t for k in ['work', 'job', 'shift']):
        return '#fff3e0'
    if any(k in t for k in ['gym', 'exercise', 'run', 'workout', 'yoga']):
        return '#e8f5e9'
    if any(k in t for k in ['study', 'read', 'homework', 'exam', 'review']):
        return '#fce4ec'
    if any(k in t for k in ['meeting', 'call', 'appointment']):
        return '#f3e5f5'
    if any(k in t for k in ['breakfast', 'lunch', 'dinner', 'meal', 'eat']):
        return '#fffde7'
    if any(k in t for k in ['sleep', 'rest', 'wind down']):
        return '#eceff1'
    return '#ffffff'


# ---------------------------------------------------------------------------
# Color utilities
# ---------------------------------------------------------------------------
def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    r, g, b = rgb
    return f'#{int(r):02x}{int(g):02x}{int(b):02x}'


def lerp_color(c1, c2, t):
    """Blend two hex colors. t=0 -> c1, t=1 -> c2."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex((r1 + (r2 - r1) * t,
                        g1 + (g2 - g1) * t,
                        b1 + (b2 - b1) * t))


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


# ---------------------------------------------------------------------------
# AnimatedButton
# ---------------------------------------------------------------------------
class AnimatedButton(tk.Frame):
    """A button that smoothly animates its background color on hover / press.

    Call `.set_text(...)` and `.set_enabled(True/False)` at runtime.
    Pack or grid the widget like any normal Frame.
    """

    RED         = '#b01b1b'
    RED_HOVER   = '#c92a2a'
    RED_ACTIVE  = '#7d1212'
    DISABLED_BG = '#d8d8d8'
    DISABLED_FG = '#999999'

    def __init__(self, parent, text, command,
                 bg=None, hover_bg=None, active_bg=None,
                 fg='#ffffff',
                 font=('Helvetica Neue', 13, 'bold'),
                 pad_x=32, pad_y=14,
                 **kwargs):
        bg        = bg        or self.RED
        hover_bg  = hover_bg  or self.RED_HOVER
        active_bg = active_bg or self.RED_ACTIVE

        super().__init__(parent, bg=bg, bd=0, highlightthickness=0,
                         cursor='hand2', **kwargs)

        self._bg        = bg
        self._hover_bg  = hover_bg
        self._active_bg = active_bg
        self._fg        = fg
        self._command   = command
        self._disabled  = False
        self._hovering  = False
        self._pressing  = False
        self._current   = bg
        self._anim_id   = None

        self.label = tk.Label(self, text=text, font=font,
                              bg=bg, fg=fg,
                              padx=pad_x, pady=pad_y,
                              cursor='hand2')
        self.label.pack(fill=tk.BOTH, expand=True)

        self.label.bind('<Enter>',           self._on_enter)
        self.label.bind('<Leave>',           self._on_leave)
        self.label.bind('<Button-1>',        self._on_press)
        self.label.bind('<ButtonRelease-1>', self._on_release)

    # ---- public API ----
    def set_text(self, text):
        self.label.config(text=text)

    def set_enabled(self, enabled):
        self._disabled = not enabled
        if enabled:
            self.label.config(fg=self._fg, cursor='hand2')
            self.config(cursor='hand2')
            self._animate_to(self._bg)
        else:
            self.label.config(fg=self.DISABLED_FG, cursor='arrow')
            self.config(cursor='arrow')
            self._animate_to(self.DISABLED_BG)

    # ---- animation ----
    def _animate_to(self, target):
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except tk.TclError:
                pass
            self._anim_id = None

        start = self._current
        steps = 12
        ms    = 14

        def tick(i):
            if not self.winfo_exists():
                return
            t = ease_out_cubic(i / steps)
            c = lerp_color(start, target, t)
            self._current = c
            try:
                self.config(bg=c)
                self.label.config(bg=c)
            except tk.TclError:
                return
            if i < steps:
                self._anim_id = self.after(ms, lambda: tick(i + 1))
            else:
                self._anim_id = None

        tick(0)

    # ---- event handlers ----
    def _on_enter(self, _):
        if self._disabled:
            return
        self._hovering = True
        if not self._pressing:
            self._animate_to(self._hover_bg)

    def _on_leave(self, _):
        if self._disabled:
            return
        self._hovering = False
        self._pressing = False
        self._animate_to(self._bg)

    def _on_press(self, _):
        if self._disabled:
            return
        self._pressing = True
        self._animate_to(self._active_bg)

    def _on_release(self, event):
        if self._disabled:
            return
        self._pressing = False
        w = self.label.winfo_width()
        h = self.label.winfo_height()
        inside = (0 <= event.x <= w) and (0 <= event.y <= h)
        if inside:
            self._animate_to(self._hover_bg)
            if self._command:
                self._command()
        else:
            self._hovering = False
            self._animate_to(self._bg)


# ---------------------------------------------------------------------------
# LinkLabel — text-only link with hover color animation
# ---------------------------------------------------------------------------
class LinkLabel(tk.Label):
    """A text link with a soft hover color transition."""

    def __init__(self, parent, text, command,
                 fg='#b01b1b', hover_fg='#7d1212', active_fg='#4a0a0a',
                 font=('Helvetica', 11, 'underline'),
                 bg=None, **kwargs):
        bg = bg or parent.cget('bg')
        super().__init__(parent, text=text, fg=fg, bg=bg,
                         font=font, cursor='hand2', **kwargs)
        self._fg        = fg
        self._hover_fg  = hover_fg
        self._active_fg = active_fg
        self._command   = command
        self._current   = fg
        self._anim_id   = None

        self.bind('<Enter>',           self._on_enter)
        self.bind('<Leave>',           self._on_leave)
        self.bind('<Button-1>',        self._on_press)
        self.bind('<ButtonRelease-1>', self._on_release)

    def _animate_to(self, target):
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except tk.TclError:
                pass
            self._anim_id = None

        start = self._current
        steps = 10
        ms    = 14

        def tick(i):
            if not self.winfo_exists():
                return
            t = ease_out_cubic(i / steps)
            c = lerp_color(start, target, t)
            self._current = c
            try:
                self.config(fg=c)
            except tk.TclError:
                return
            if i < steps:
                self._anim_id = self.after(ms, lambda: tick(i + 1))
            else:
                self._anim_id = None

        tick(0)

    def _on_enter(self, _):
        self._animate_to(self._hover_fg)

    def _on_leave(self, _):
        self._animate_to(self._fg)

    def _on_press(self, _):
        self._animate_to(self._active_fg)

    def _on_release(self, _):
        self._animate_to(self._hover_fg)
        if self._command:
            self._command()