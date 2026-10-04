import tkinter as tk

# Deep red — same as before
RED   = '#b01b1b'
BLACK = '#0a0a0a'


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_in_cubic(t):
    return t ** 3


def _lerp_color(c1, c2, t):
    """Blend two hex colors. t=0 -> c1, t=1 -> c2."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f'#{r:02x}{g:02x}{b:02x}'


class SplashView(tk.Frame):
    """Cinematic ORBIT splash.

    Sequence:
      1. Each letter of ORBIT wipes in left-to-right, staggered,
         with a cubic ease-out (fast then settle).
      2. A thin black rule draws outward from centre beneath the
         word with a slight overshoot, then settles.
      3. A letterspaced subtitle rises and fades from red to black.
      4. Hold.
      5. Reverse: subtitle fades back to red and vanishes, rule
         retracts, letters wipe out.

    Click anywhere to skip.
    """

    LETTERS        = list("ORBIT")
    LETTER_STAGGER = 120
    LETTER_WIPE_MS = 480
    LINE_DELAY_AFTER = 180
    LINE_MS        = 540
    SUBTITLE_DELAY = 100
    HOLD_MS        = 1600
    EXIT_LINE_MS   = 420
    EXIT_LETTER_MS = 460
    EXIT_STAGGER   = 110
    FINAL_PAUSE_MS = 260

    # Vertical position of the word's centre — lower = higher on screen
    V_CENTER_RATIO = 0.42

    def __init__(self, parent, on_done):
        super().__init__(parent, bg=RED)
        self.on_done   = on_done
        self._done     = False
        self._timers   = []
        self._letters  = []
        self._line_id  = None
        self._sub_id   = None
        self._cx       = 0
        self._sub_y    = 0
        self._line_x1  = 0
        self._line_x2  = 0
        self._line_y   = 0

        self.canvas = tk.Canvas(self, bg=RED, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        for w in (self, self.canvas):
            w.bind('<Button-1>', lambda e: self._finish_early())

    # ----------------------------------------------------------
    def start(self):
        self.after(50, self._build)

    # ----------------------------------------------------------
    # Layout / build
    # ----------------------------------------------------------
    def _build(self):
        if self._done or not self.winfo_exists():
            return
        W = self.canvas.winfo_width()
        H = self.canvas.winfo_height()
        if W < 120 or H < 120:
            self._schedule(40, self._build)
            return

        self.canvas.delete('all')
        cx = W // 2
        cy = int(H * self.V_CENTER_RATIO)
        self._cx = cx

        # Font size scales with the smaller of H or W so the word
        # never overflows a narrow window.
        size_by_h = int(H * 0.28)
        size_by_w = int(W * 0.22)
        size = max(72, min(size_by_h, size_by_w, 220))
        main_font = ('Helvetica Neue', size, 'bold')

        # ---- Pass 1: measure each letter ----
        measures = []
        x = 0
        for ch in self.LETTERS:
            item = self.canvas.create_text(
                x, cy, text=ch, anchor='w',
                font=main_font, fill=BLACK,
            )
            b = self.canvas.bbox(item)
            if not b:
                self.canvas.delete('all')
                self._schedule(40, self._build)
                return
            w = b[2] - b[0]
            measures.append((item, w))
            x += w

        total  = x
        offset = cx - total // 2

        # ---- Pass 2: shift letters to centre, attach masks ----
        self._letters = []
        for item, _w in measures:
            self.canvas.move(item, offset, 0)
            b = self.canvas.bbox(item)
            mask = self.canvas.create_rectangle(
                b[0] - 1, b[1] - 8, b[2] + 1, b[3] + 8,
                fill=RED, outline=RED,
            )
            self._letters.append({
                'item': item,
                'mask': mask,
                'x1': b[0] - 1,
                'y1': b[1] - 8,
                'x2': b[2] + 1,
                'y2': b[3] + 8,
            })

        # ---- Rule beneath the word ----
        word_bottom = max(L['y2'] for L in self._letters)
        word_left   = min(L['x1'] for L in self._letters)
        word_right  = max(L['x2'] for L in self._letters)

        self._line_y  = word_bottom + 40
        self._line_x1 = word_left + 16
        self._line_x2 = word_right - 16
        self._line_id = self.canvas.create_line(
            cx, self._line_y, cx, self._line_y,
            fill=BLACK, width=2, capstyle='round',
            state='hidden',
        )

        # ---- Letterspaced subtitle ----
        sub_size = max(11, min(int(H * 0.022), 20))
        sub_text = ' '.join("WEEKLY SCHEDULER")
        self._sub_y = self._line_y + 36
        self._sub_id = self.canvas.create_text(
            cx, self._sub_y, text=sub_text,
            font=('Helvetica Neue', sub_size, 'normal'),
            fill=RED, anchor='c', state='hidden',
        )

        self._play_entrance()

    # ----------------------------------------------------------
    # Entrance
    # ----------------------------------------------------------
    def _play_entrance(self):
        for i, L in enumerate(self._letters):
            self._schedule(i * self.LETTER_STAGGER,
                           lambda L=L: self._reveal_letter(L))

        last_start  = (len(self._letters) - 1) * self.LETTER_STAGGER
        line_at     = last_start + self.LETTER_WIPE_MS + self.LINE_DELAY_AFTER
        subtitle_at = line_at + self.LINE_MS + self.SUBTITLE_DELAY
        exit_at     = subtitle_at + 300 + self.HOLD_MS

        self._schedule(line_at, self._draw_line)
        self._schedule(subtitle_at, self._show_subtitle)
        self._schedule(exit_at, self._play_exit)

    def _reveal_letter(self, L):
        if self._done or not self.winfo_exists():
            return
        x1, y1, x2, y2 = L['x1'], L['y1'], L['x2'], L['y2']
        width = x2 - x1
        steps = 18
        step_ms = max(1, self.LETTER_WIPE_MS // steps)

        def tick(i):
            if self._done or not self.winfo_exists():
                return
            t   = _ease_out_cubic(i / steps)
            nx1 = x1 + t * width
            try:
                self.canvas.coords(L['mask'], nx1, y1, x2, y2)
            except tk.TclError:
                return
            if i < steps:
                self._schedule(step_ms, lambda: tick(i + 1))
            else:
                try:
                    self.canvas.delete(L['mask'])
                except tk.TclError:
                    pass
                L['mask'] = None

        tick(0)

    def _draw_line(self):
        """Draw the rule outward with a slight overshoot, then settle."""
        if self._done or not self.winfo_exists():
            return
        try:
            self.canvas.itemconfig(self._line_id, state='normal')
        except tk.TclError:
            return

        cx        = (self._line_x1 + self._line_x2) // 2
        full_half = (self._line_x2 - self._line_x1) / 2
        steps     = 22
        step_ms   = max(1, self.LINE_MS // steps)
        overshoot = 1.055       # peak 5.5% past the target
        split     = 0.72        # phase split (draw then settle)

        def tick(i):
            if self._done or not self.winfo_exists():
                return
            t = i / steps
            if t <= split:
                tt    = t / split
                scale = _ease_out_cubic(tt) * overshoot
            else:
                tt    = (t - split) / (1.0 - split)
                scale = overshoot - (overshoot - 1.0) * _ease_out_cubic(tt)
            half = full_half * scale
            try:
                self.canvas.coords(self._line_id,
                                   cx - half, self._line_y,
                                   cx + half, self._line_y)
            except tk.TclError:
                return
            if i < steps:
                self._schedule(step_ms, lambda: tick(i + 1))

        tick(0)

    def _show_subtitle(self):
        """Rise into place while fading from red to black."""
        if self._done or not self.winfo_exists():
            return
        try:
            self.canvas.itemconfig(self._sub_id, state='normal', fill=RED)
        except tk.TclError:
            return

        cx      = self._cx
        y_start = self._sub_y + 10
        y_end   = self._sub_y
        steps   = 18
        step_ms = 22

        try:
            self.canvas.coords(self._sub_id, cx, y_start)
        except tk.TclError:
            return

        def tick(i):
            if self._done or not self.winfo_exists():
                return
            t = _ease_out_cubic(i / steps)
            y = y_start + (y_end - y_start) * t
            c = _lerp_color(RED, BLACK, t)
            try:
                self.canvas.coords(self._sub_id, cx, y)
                self.canvas.itemconfig(self._sub_id, fill=c)
            except tk.TclError:
                return
            if i < steps:
                self._schedule(step_ms, lambda: tick(i + 1))

        tick(0)

    # ----------------------------------------------------------
    # Exit
    # ----------------------------------------------------------
    def _play_exit(self):
        if self._done or not self.winfo_exists():
            return

        # Subtitle fades back to red, then disappears
        self._fade_subtitle_out()
        # Rule retracts to centre
        self._retract_line()
        # Letters wipe out, staggered
        for i, L in enumerate(self._letters):
            self._schedule(180 + i * self.EXIT_STAGGER,
                           lambda L=L: self._cover_letter(L))

        last = 180 + (len(self._letters) - 1) * self.EXIT_STAGGER
        self._schedule(last + self.EXIT_LETTER_MS + self.FINAL_PAUSE_MS,
                       self._finish)

    def _fade_subtitle_out(self):
        if self._done or not self.winfo_exists() or self._sub_id is None:
            return
        steps   = 14
        step_ms = 18

        def tick(i):
            if self._done or not self.winfo_exists():
                return
            t = i / steps
            c = _lerp_color(BLACK, RED, t)
            try:
                self.canvas.itemconfig(self._sub_id, fill=c)
            except tk.TclError:
                return
            if i < steps:
                self._schedule(step_ms, lambda: tick(i + 1))
            else:
                try:
                    self.canvas.delete(self._sub_id)
                except tk.TclError:
                    pass
                self._sub_id = None

        tick(0)

    def _retract_line(self):
        cx        = (self._line_x1 + self._line_x2) // 2
        full_half = (self._line_x2 - self._line_x1) / 2
        steps     = 16
        step_ms   = max(1, self.EXIT_LINE_MS // steps)

        def tick(i):
            if self._done or not self.winfo_exists():
                return
            t = _ease_in_cubic(i / steps)
            half = full_half * (1 - t)
            try:
                self.canvas.coords(self._line_id,
                                   cx - half, self._line_y,
                                   cx + half, self._line_y)
            except tk.TclError:
                return
            if i < steps:
                self._schedule(step_ms, lambda: tick(i + 1))

        tick(0)

    def _cover_letter(self, L):
        if self._done or not self.winfo_exists():
            return
        x1, y1, x2, y2 = L['x1'], L['y1'], L['x2'], L['y2']
        width = x2 - x1

        try:
            mask = self.canvas.create_rectangle(
                x1, y1, x1, y2, fill=RED, outline=RED,
            )
        except tk.TclError:
            return

        steps   = 16
        step_ms = max(1, self.EXIT_LETTER_MS // steps)

        def tick(i):
            if self._done or not self.winfo_exists():
                return
            t = _ease_in_cubic(i / steps)
            nx2 = x1 + t * width
            try:
                self.canvas.coords(mask, x1, y1, nx2, y2)
            except tk.TclError:
                return
            if i < steps:
                self._schedule(step_ms, lambda: tick(i + 1))

        tick(0)

    # ----------------------------------------------------------
    # Endings
    # ----------------------------------------------------------
    def _finish(self):
        if self._done:
            return
        self._done = True
        self._cancel_all()
        self.on_done()

    def _finish_early(self):
        self._finish()

    # ----------------------------------------------------------
    # Timer helpers
    # ----------------------------------------------------------
    def _schedule(self, ms, fn):
        if self._done or not self.winfo_exists():
            return None
        try:
            tid = self.after(ms, fn)
            self._timers.append(tid)
            return tid
        except tk.TclError:
            return None

    def _cancel_all(self):
        for tid in self._timers:
            try:
                self.after_cancel(tid)
            except tk.TclError:
                pass
        self._timers = []