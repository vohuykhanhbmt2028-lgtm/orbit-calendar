import tkinter as tk
from config import DAYS_FULL, DAYS_SHORT


BRAND_RED         = '#b01b1b'
BRAND_DEEP        = '#7d1212'
CARD_BG           = '#fbfbfb'
CARD_HOVER        = '#fef7f7'
CARD_BORDER       = '#ececec'
CARD_HOVER_BORDER = '#b01b1b'


class VariantsView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg='#ffffff')
        self.app = app

    def reset(self):
        """Clear the variants display — the wizard is done."""
        for w in self.winfo_children():
            w.destroy()

    # =================================================================
    def render(self, variants):
        for w in self.winfo_children():
            w.destroy()

        # ---------- Header ----------
        header = tk.Frame(self, bg='#ffffff')
        header.pack(fill=tk.X, padx=50, pady=(40, 26))

        top = tk.Frame(header, bg='#ffffff')
        top.pack(fill=tk.X)

        tk.Label(top, text=' '.join("CHOOSE A PLAN"),
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg=BRAND_RED).pack(side=tk.LEFT)

        tk.Label(top, text=f"{len(variants)} OPTIONS",
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg='#cccccc').pack(side=tk.RIGHT)

        tk.Label(header, text="Pick your favorite.",
                 font=('Helvetica Neue', 28, 'bold'),
                 bg='#ffffff', fg='#1a1a1a').pack(anchor='w', pady=(12, 0))

        tk.Label(header,
         text="Four different strategies for your week — same events, different rhythm. Click any card.",
         font=('Helvetica', 13),
         bg='#ffffff', fg='#888').pack(anchor='w', pady=(8, 0))

        # ---------- Cards ----------
        grid = tk.Frame(self, bg='#ffffff')
        grid.pack(fill=tk.BOTH, expand=True, padx=50, pady=(0, 20))

        cols = 2 if len(variants) > 1 else 1
        for i, v in enumerate(variants):
            r, c = divmod(i, cols)
            self._make_card(grid, v, i).grid(
                row=r, column=c, sticky='nsew', padx=8, pady=8)
        for c in range(cols):
            grid.columnconfigure(c, weight=1, uniform='col')
        rows = (len(variants) + cols - 1) // cols
        for r in range(rows):
            grid.rowconfigure(r, weight=1, uniform='row')

        # ---------- Footer ----------
        footer = tk.Frame(self, bg='#ffffff')
        footer.pack(fill=tk.X, padx=50, pady=(0, 30))

        from ui_helpers import LinkLabel
        LinkLabel(footer, text="←  Back to setup",
                  command=lambda: self.app.show_setup(step=3),
                  fg='#888888', hover_fg='#1a1a1a', active_fg=BRAND_RED,
                  bg='#ffffff').pack(side=tk.LEFT)

        LinkLabel(footer, text="Regenerate  ↻",
                  command=self.app.regenerate_variants,
                  fg='#888888', hover_fg=BRAND_RED, active_fg=BRAND_DEEP,
                  font=('Helvetica', 11, 'underline'),
                  bg='#ffffff').pack(side=tk.RIGHT)

    # =================================================================
    # Card
    # =================================================================
    def _make_card(self, parent, variant, index):
        name         = variant.get('name', 'Variant')
        tagline      = variant.get('tagline', '')
        schedule     = variant.get('schedule', {})
        number_text  = f"{index + 1:02d}"

        card = tk.Frame(parent, bg=CARD_BG,
                        highlightthickness=1,
                        highlightbackground=CARD_BORDER,
                        highlightcolor=CARD_BORDER,
                        bd=0, cursor='hand2')

        inner = tk.Frame(card, bg=CARD_BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=28, pady=26)

        # ---- Top row: name + number badge ----
        top = tk.Frame(inner, bg=CARD_BG)
        top.pack(fill=tk.X)

        tk.Label(top, text=name,
                 font=('Helvetica Neue', 22, 'bold'),
                 bg=CARD_BG, fg='#1a1a1a', anchor='w')\
            .pack(side=tk.LEFT)

        badge = tk.Label(top, text=number_text,
                         font=('Helvetica Neue', 26),
                         bg=CARD_BG, fg='#e5e5e5', anchor='e')
        badge.pack(side=tk.RIGHT)

        # ---- Tagline ----
        tk.Label(inner, text=tagline,
                 font=('Helvetica', 13),
                 bg=CARD_BG, fg='#888', anchor='w',
                 justify='left', wraplength=440)\
            .pack(anchor='w', pady=(8, 0))

        # ---- Elastic spacer so chart sits toward the bottom ----
        tk.Frame(inner, bg=CARD_BG).pack(fill=tk.BOTH, expand=True)

        # ---- Bar chart ----
        chart = tk.Canvas(inner, bg=CARD_BG, height=70,
                          highlightthickness=0, bd=0)
        chart.pack(fill=tk.X)
        chart.after(80, lambda c=chart, s=schedule: self._draw_bars(c, s))

        # ---- Stats row ----
        stats = self._compute_stats(schedule)
        stat_row = tk.Frame(inner, bg=CARD_BG)
        stat_row.pack(fill=tk.X, pady=(20, 0))

        tk.Label(stat_row, text=f"{stats['total']} events",
                 font=('Helvetica Neue', 11, 'bold'),
                 bg=CARD_BG, fg='#333').pack(side=tk.LEFT)

        tk.Label(stat_row, text="·",
                 font=('Helvetica Neue', 11),
                 bg=CARD_BG, fg='#dddddd').pack(side=tk.LEFT, padx=10)

        tk.Label(stat_row, text=stats['focus'],
                 font=('Helvetica Neue', 11),
                 bg=CARD_BG, fg='#888').pack(side=tk.LEFT)

        # ---- Hover ----
        def set_hover(on):
            try:
                bg = CARD_HOVER if on else CARD_BG
                bd = CARD_HOVER_BORDER if on else CARD_BORDER
                card.config(bg=bg, highlightbackground=bd, highlightcolor=bd)
                self._set_bg_recursive(card, bg)
                if on:
                    badge.config(text="→", fg=BRAND_RED,
                                 font=('Helvetica Neue', 26, 'bold'))
                else:
                    badge.config(text=number_text, fg='#e5e5e5',
                                 font=('Helvetica Neue', 26))
            except tk.TclError:
                pass

        def on_leave(_e):
            try:
                x, y = card.winfo_pointerxy()
                under = card.winfo_containing(x, y)
            except tk.TclError:
                under = None
            if under is not None:
                anc = under
                while anc is not None:
                    if anc is card:
                        return
                    anc = anc.master
            set_hover(False)

        for w in self._collect_widgets(card):
            w.bind('<Button-1>', lambda e, v=variant: self.app.pick_variant(v))
            w.bind('<Enter>',    lambda e: set_hover(True))
            w.bind('<Leave>',    on_leave)

        return card

    # =================================================================
    def _collect_widgets(self, root):
        out = [root]
        for child in root.winfo_children():
            out.extend(self._collect_widgets(child))
        return out

    def _set_bg_recursive(self, w, bg):
        for child in w.winfo_children():
            try:
                if isinstance(child, (tk.Canvas, tk.Label, tk.Frame)):
                    child.config(bg=bg)
                self._set_bg_recursive(child, bg)
            except tk.TclError:
                pass

    # =================================================================
    # Bar chart
    # =================================================================
    def _draw_bars(self, canvas, schedule):
        try:
            canvas.update_idletasks()
            W = canvas.winfo_width()
        except tk.TclError:
            return
        if W < 20:
            canvas.after(40, lambda: self._draw_bars(canvas, schedule))
            return

        canvas.delete('all')

        H          = 70
        label_h    = 20
        top_pad    = 6
        chart_base = H - label_h

        n       = 7
        gap     = 10
        bar_w   = 10
        total_w = n * bar_w + (n - 1) * gap
        start_x = (W - total_w) / 2

        counts    = [len(schedule.get(day, [])) for day in DAYS_FULL]
        max_count = max(counts) if counts else 1
        max_count = max(max_count, 1)

        usable_h = chart_base - top_pad

        for i, (short, count) in enumerate(zip(DAYS_SHORT, counts)):
            x = start_x + i * (bar_w + gap) + bar_w / 2

            if count == 0:
                # Tiny grey stub
                y0 = chart_base - 6
                color = '#e4e4e4'
                canvas.create_rectangle(x - bar_w / 2, y0,
                                        x + bar_w / 2, chart_base,
                                        fill=color, outline='')
            else:
                bar_h = 14 + (count / max_count) * (usable_h - 14)
                y0 = chart_base - bar_h
                color = BRAND_RED

                # Body (flat)
                canvas.create_rectangle(x - bar_w / 2, y0 + bar_w / 2,
                                        x + bar_w / 2, chart_base,
                                        fill=color, outline='')
                # Rounded top cap
                canvas.create_oval(x - bar_w / 2, y0,
                                   x + bar_w / 2, y0 + bar_w,
                                   fill=color, outline='')

            # Day label
            canvas.create_text(x, chart_base + 12,
                               text=short,
                               font=('Helvetica', 9, 'bold'),
                               fill='#b8b8b8')

    # =================================================================
    def _compute_stats(self, schedule):
        total = sum(len(schedule.get(day, [])) for day in DAYS_FULL)

        morning = evening = 0
        for day in DAYS_FULL:
            for ev in schedule.get(day, []):
                t = ev.get('time', '').upper()
                if 'AM' in t:
                    morning += 1
                elif 'PM' in t:
                    evening += 1

        if morning + evening == 0:
            focus = 'Quiet week'
        elif morning > evening * 1.4:
            focus = 'Morning-heavy'
        elif evening > morning * 1.4:
            focus = 'Evening-heavy'
        else:
            focus = 'Evenly spread'

        return {'total': total, 'focus': focus}