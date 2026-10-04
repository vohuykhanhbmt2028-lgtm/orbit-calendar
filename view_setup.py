import tkinter as tk
import icons
from tkinter import ttk

from config import (CORE_CATEGORIES, EXTRA_CATEGORIES,
                    TIME_OPTIONS, DURATION_OPTIONS, TIMES_PER_WEEK,
                    WHEN_OPTIONS, STUDY_DAYS, STUDY_HOURS,
                    DAYS_SHORT)
from ui_helpers import (AnimatedButton, LinkLabel,
                        lerp_color, ease_out_cubic,
                        form_card, field_label,
                        clean_entry, clean_combo,
                        day_pills, add_another_tile,
                        small_link_button)


CARD_NORMAL   = ('#fafafa', '#e8e8e8')
CARD_HOVER    = ('#f4f4f4', '#cfcfcf')
CARD_SELECTED = ('#fbe9e9', '#b01b1b')


class SetupView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg='#ffffff')
        self.app = app
        self.step = 1
        self.show_extras = False
        self._class_rows = []
        self._work_rows = []
        self.category_cards = {}
        self.show_step(1)
    def reset(self):
        """Wipe the wizard and return to a clean step 1."""
        self.show_extras = False
        self._class_rows = []
        self._work_rows = []
        self.category_cards = {}
        self.step = 1
        self._clear()
        self._build_step1()

    # ---------- dispatch ----------
    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def show_step(self, n):
        self.step = n
        self._clear()
        if n == 1:
            self._build_step1()
        elif n == 2:
            self._build_step2()
        elif n == 3:
            self._build_step3()

    # =================================================================
    # STEP 1 — CATEGORIES
    # =================================================================
    def _build_step1(self):
        outer = tk.Frame(self, bg='#ffffff')
        outer.pack(fill=tk.BOTH, expand=True, padx=50, pady=(40, 30))

        header = tk.Frame(outer, bg='#ffffff')
        header.pack(fill=tk.X, pady=(0, 30))

        top_row = tk.Frame(header, bg='#ffffff')
        top_row.pack(fill=tk.X)

        tk.Label(top_row, text=' '.join("WELCOME TO ORBIT"),
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg='#b01b1b').pack(side=tk.LEFT)

        tk.Label(top_row, text="STEP 1 OF 3",
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg='#cccccc').pack(side=tk.RIGHT)

        tk.Label(header, text="Let's start with your week.",
                 font=('Helvetica Neue', 28, 'bold'),
                 bg='#ffffff', fg='#1a1a1a').pack(anchor='w', pady=(12, 0))

        tk.Label(header, text="Tap anything that applies. You can fill in details next.",
                 font=('Helvetica', 13),
                 bg='#ffffff', fg='#888').pack(anchor='w', pady=(8, 0))

        grid = tk.Frame(outer, bg='#ffffff')
        grid.pack(fill=tk.BOTH, expand=True)

        self.category_cards = {}

        core_grid = tk.Frame(grid, bg='#ffffff')
        core_grid.pack(fill='x')
        for i, (key, title, desc) in enumerate(CORE_CATEGORIES):
            r, c = divmod(i, 2)
            self._make_category_card(core_grid, key, title, desc)\
                .grid(row=r, column=c, sticky='nsew', padx=6, pady=6)
        core_grid.columnconfigure(0, weight=1)
        core_grid.columnconfigure(1, weight=1)

        self.more_btn = LinkLabel(
            grid, text="+  Show more options",
            command=self._toggle_more,
            fg='#888888', hover_fg='#1a1a1a', active_fg='#b01b1b',
            font=('Helvetica', 11, 'bold'),
            bg='#ffffff', underline=False)
        self.more_btn.pack(anchor='w', pady=(14, 0))

        self.extra_grid = tk.Frame(grid, bg='#ffffff')
        for i, (key, title, desc) in enumerate(EXTRA_CATEGORIES):
            r, c = divmod(i, 2)
            self._make_category_card(self.extra_grid, key, title, desc)\
                .grid(row=r, column=c, sticky='nsew', padx=6, pady=6)
        self.extra_grid.columnconfigure(0, weight=1)
        self.extra_grid.columnconfigure(1, weight=1)

        if self.show_extras:
            self.extra_grid.pack(fill='x', pady=(6, 0))
            self.more_btn.config(text="−  Show fewer options")

        bottom = tk.Frame(outer, bg='#ffffff')
        bottom.pack(fill=tk.X, pady=(30, 0))

        LinkLabel(bottom,
                  text="Skip — just chat instead  →",
                  command=lambda: self.app.show_chat(),
                  fg='#b01b1b', hover_fg='#7d1212', active_fg='#4a0a0a',
                  bg='#ffffff').pack(side=tk.LEFT)

        AnimatedButton(bottom, "Continue  →",
                       command=lambda: self.show_step(2),
                       font=('Helvetica Neue', 13, 'bold'),
                       pad_x=34, pad_y=14)\
            .pack(side=tk.RIGHT)

    def _toggle_more(self):
        self.show_extras = not self.show_extras
        if self.show_extras:
            self.extra_grid.pack(fill='x', pady=(6, 0))
            self.more_btn.config(text="−  Show fewer options")
        else:
            self.extra_grid.pack_forget()
            self.more_btn.config(text="+  Show more options")

    def _make_category_card(self, parent, key, title, desc):
        bg, border = CARD_NORMAL
        card = tk.Frame(parent, bg=bg,
                        highlightthickness=1, highlightbackground=border,
                        bd=0, cursor='hand2')

        inner = tk.Frame(card, bg=bg)
        inner.pack(fill=tk.BOTH, expand=True, padx=22, pady=20)

        top_row = tk.Frame(inner, bg=bg)
        top_row.pack(fill='x')

        ICON_SIZE = 40
        icon_canvas = tk.Canvas(top_row, width=ICON_SIZE, height=ICON_SIZE,
                                bg=bg, highlightthickness=0, bd=0,
                                cursor='hand2')
        icon_canvas.pack(side=tk.LEFT)
        icons.render(icon_canvas, key, ICON_SIZE, bg=bg)

        title_lbl = tk.Label(top_row, text=title,
                             font=('Helvetica Neue', 15, 'bold'),
                             bg=bg, fg='#1a1a1a', anchor='w')
        title_lbl.pack(side=tk.LEFT, padx=(14, 0))

        desc_lbl = tk.Label(inner, text=desc, font=('Helvetica', 11),
                            bg=bg, fg='#8a8a8a', anchor='w',
                            justify='left', wraplength=330)
        desc_lbl.pack(anchor='w', pady=(10, 0))

        widgets = [card, inner, top_row, icon_canvas, title_lbl, desc_lbl]
        for w in widgets:
            w.bind('<Button-1>', lambda e, k=key: self._toggle_category(k))
            w.bind('<Enter>',    lambda e, k=key: self._on_card_enter(k))
            w.bind('<Leave>',    lambda e, k=key, c=card: self._on_card_leave(k, c))

        self.category_cards[key] = {
            'card': card, 'inner': inner, 'top_row': top_row,
            'icon_canvas': icon_canvas,
            'title': title_lbl, 'desc': desc_lbl,
            'bg_now': bg, 'border_now': border, 'anim_id': None,
        }

        if key in self.app.form.categories:
            self._snap_card(key, CARD_SELECTED)
        return card

    def _snap_card(self, key, state):
        bg, border = state
        c = self.category_cards[key]
        c['card'].config(bg=bg, highlightbackground=border)
        for k in ('inner', 'top_row', 'icon_canvas', 'title', 'desc'):
            c[k].config(bg=bg)
        c['bg_now']     = bg
        c['border_now'] = border

    def _animate_card(self, key, target_bg, target_border):
        c = self.category_cards.get(key)
        if not c:
            return
        if c.get('anim_id') is not None:
            try:
                c['card'].after_cancel(c['anim_id'])
            except tk.TclError:
                pass
            c['anim_id'] = None

        start_bg     = c['bg_now']
        start_border = c['border_now']
        steps        = 10
        ms           = 14

        def tick(i):
            cc = self.category_cards.get(key)
            if not cc:
                return
            t = ease_out_cubic(i / steps)
            bg     = lerp_color(start_bg,     target_bg,     t)
            border = lerp_color(start_border, target_border, t)
            try:
                cc['card'].config(bg=bg, highlightbackground=border)
                for k in ('inner', 'top_row', 'icon_canvas', 'title', 'desc'):
                    cc[k].config(bg=bg)
            except tk.TclError:
                return
            cc['bg_now']     = bg
            cc['border_now'] = border
            if i < steps:
                cc['anim_id'] = cc['card'].after(ms, lambda: tick(i + 1))
            else:
                cc['anim_id'] = None

        tick(0)

    def _toggle_category(self, key):
        self.app._mark_dirty()
        if key in self.app.form.categories:
            self.app.form.categories.remove(key)
            self._animate_card(key, *CARD_HOVER)
        else:
            self.app.form.categories.add(key)
            self._animate_card(key, *CARD_SELECTED)

    def _on_card_enter(self, key):
        if key in self.app.form.categories:
            return
        self._animate_card(key, *CARD_HOVER)

    def _on_card_leave(self, key, card):
        if key in self.app.form.categories:
            return
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
        self._animate_card(key, *CARD_NORMAL)

    # =================================================================
    # STEP 2 — FORMS
    # =================================================================
    def _build_step2(self):
        for a in ('_class_rows', '_work_rows',
                  'gym_times_var', 'gym_when_var', 'gym_dur_var',
                  'study_hours_var', 'study_when_var', 'study_days_var',
                  'hobbies_times_var', 'hobbies_when_var', 'hobbies_dur_var',
                  'errands_times_var', 'errands_when_var',
                  'meals_breakfast_var', 'meals_lunch_var', 'meals_dinner_var',
                  'sleep_bed_var', 'sleep_wake_var', 'other_text'):
            if hasattr(self, a):
                delattr(self, a)
        self._class_rows = []
        self._work_rows = []

        header = tk.Frame(self, bg='#ffffff')
        header.pack(fill=tk.X, padx=50, pady=(40, 24))

        top_row = tk.Frame(header, bg='#ffffff')
        top_row.pack(fill=tk.X)
        tk.Label(top_row, text=' '.join("DETAILS"),
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg='#b01b1b').pack(side=tk.LEFT)
        tk.Label(top_row, text="STEP 2 OF 3",
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg='#cccccc').pack(side=tk.RIGHT)

        tk.Label(header, text="Fill in the details",
                 font=('Helvetica Neue', 28, 'bold'),
                 bg='#ffffff', fg='#1a1a1a').pack(anchor='w', pady=(12, 0))
        tk.Label(header,
                 text="Just the basics — everything has a sensible default, so skip what you don't need.",
                 font=('Helvetica', 13),
                 bg='#ffffff', fg='#888').pack(anchor='w', pady=(8, 0))

        footer = tk.Frame(self, bg='#ffffff')
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=50, pady=(20, 30))

        tk.Frame(footer, bg='#eeeeee', height=1).pack(fill=tk.X, pady=(0, 20))

        row = tk.Frame(footer, bg='#ffffff')
        row.pack(fill=tk.X)

        LinkLabel(row, text="←  Back",
                  command=lambda: self.show_step(1),
                  fg='#888888', hover_fg='#1a1a1a', active_fg='#b01b1b',
                  font=('Helvetica', 11, 'underline'),
                  bg='#ffffff').pack(side=tk.LEFT)

        AnimatedButton(row, "Review  →",
                       command=self._collect_and_review,
                       font=('Helvetica Neue', 13, 'bold'),
                       pad_x=34, pad_y=14)\
            .pack(side=tk.RIGHT)

        wrapper = tk.Frame(self, bg='#ffffff')
        wrapper.pack(fill=tk.BOTH, expand=True, padx=50)

        canvas = tk.Canvas(wrapper, bg='#ffffff', highlightthickness=0)
        scroll = tk.Scrollbar(wrapper, orient='vertical',
                              command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        body = tk.Frame(canvas, bg='#ffffff')
        canvas.create_window((0, 0), window=body, anchor='nw')

        def _on_configure(_event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        body.bind('<Configure>', _on_configure)
        canvas.bind('<Configure>',
                    lambda e: canvas.itemconfig(1, width=e.width - 4))

        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 3)), 'units')
            except tk.TclError:
                pass

        def _enter(_event):
            canvas.bind_all('<MouseWheel>', _on_mousewheel)

        def _leave(_event):
            try:
                canvas.unbind_all('<MouseWheel>')
            except tk.TclError:
                pass

        canvas.bind('<Enter>', _enter)
        canvas.bind('<Leave>', _leave)

        order = ['classes', 'work', 'sleep', 'meals',
                 'gym', 'study', 'hobbies', 'errands', 'other']
        for key in order:
            if key not in self.app.form.categories:
                continue
            builder = getattr(self, f'_form_{key}', None)
            if builder:
                builder(body)

        tk.Frame(body, bg='#ffffff', height=20).pack()

    def _field_row(self, parent, label, var, options=None, entry_width=30,
                   combo_width=14):
        wrap = tk.Frame(parent, bg='#ffffff')
        field_label(wrap, label)
        if options is None:
            clean_entry(wrap, var, width=entry_width).pack(anchor='w', ipady=8)
        else:
            clean_combo(wrap, var, options, width=combo_width)\
                .pack(anchor='w', ipady=4)
        return wrap

    # ---- forms ----
    def _form_classes(self, parent):
        card, body = form_card(parent, "Classes & lectures",
                                "Weekly lectures, seminars, labs")
        self._class_rows = []

        def add_row(entry=None):
            entry = entry or {'name': '', 'days': set(),
                              'start': '9:00 AM', 'duration': '1h'}
            row = tk.Frame(body, bg='#ffffff',
                           highlightthickness=1,
                           highlightbackground='#f0f0f0',
                           bd=0)
            row.pack(fill='x', pady=(0, 12))

            inner = tk.Frame(row, bg='#ffffff')
            inner.pack(fill='x', padx=18, pady=18)

            head = tk.Frame(inner, bg='#ffffff')
            head.pack(fill='x', pady=(0, 12))
            tk.Label(head, text="Class",
                     font=('Helvetica', 10, 'bold'),
                     bg='#ffffff', fg='#aaaaaa').pack(side=tk.LEFT)

            def remove():
                self._remove_row(self._class_rows, row)
            small_link_button(head, "Remove", remove).pack(side=tk.RIGHT)

            name_var = tk.StringVar(value=entry.get('name', ''))
            self._field_row(inner, "Class name", name_var,
                            entry_width=40).pack(fill='x', pady=(0, 14))

            field_label(inner, "Days")
            days_h = day_pills(inner, initial=entry.get('days', set()))
            days_h.pack(anchor='w', pady=(0, 14))

            time_row = tk.Frame(inner, bg='#ffffff')
            time_row.pack(fill='x')

            start_var = tk.StringVar(value=entry.get('start', '9:00 AM'))
            self._field_row(time_row, "Starts at", start_var,
                            options=TIME_OPTIONS, combo_width=12)\
                .pack(side=tk.LEFT, padx=(0, 20))

            dur_var = tk.StringVar(value=entry.get('duration', '1h'))
            self._field_row(time_row, "Duration", dur_var,
                            options=DURATION_OPTIONS, combo_width=10)\
                .pack(side=tk.LEFT)

            self._class_rows.append((row, name_var, days_h,
                                      start_var, dur_var))

        for e in self.app.form.classes:
            add_row(e)

        add_another_tile(body, "Add another class", add_row)

    def _form_work(self, parent):
        card, body = form_card(parent, "Work / job", "Recurring shifts")
        self._work_rows = []

        def add_row(entry=None):
            entry = entry or {'days': set(),
                              'start': '9:00 AM', 'end': '5:00 PM'}
            row = tk.Frame(body, bg='#ffffff',
                           highlightthickness=1,
                           highlightbackground='#f0f0f0',
                           bd=0)
            row.pack(fill='x', pady=(0, 12))

            inner = tk.Frame(row, bg='#ffffff')
            inner.pack(fill='x', padx=18, pady=18)

            head = tk.Frame(inner, bg='#ffffff')
            head.pack(fill='x', pady=(0, 12))
            tk.Label(head, text="Shift",
                     font=('Helvetica', 10, 'bold'),
                     bg='#ffffff', fg='#aaaaaa').pack(side=tk.LEFT)

            def remove():
                self._remove_row(self._work_rows, row)
            small_link_button(head, "Remove", remove).pack(side=tk.RIGHT)

            field_label(inner, "Days")
            days_h = day_pills(inner, initial=entry.get('days', set()))
            days_h.pack(anchor='w', pady=(0, 14))

            time_row = tk.Frame(inner, bg='#ffffff')
            time_row.pack(fill='x')

            start_var = tk.StringVar(value=entry.get('start', '9:00 AM'))
            self._field_row(time_row, "From", start_var,
                            options=TIME_OPTIONS, combo_width=12)\
                .pack(side=tk.LEFT, padx=(0, 20))

            end_var = tk.StringVar(value=entry.get('end', '5:00 PM'))
            self._field_row(time_row, "To", end_var,
                            options=TIME_OPTIONS, combo_width=12)\
                .pack(side=tk.LEFT)

            self._work_rows.append((row, days_h, start_var, end_var))

        for e in self.app.form.work:
            add_row(e)

        add_another_tile(body, "Add another shift", add_row)

    def _form_sleep(self, parent):
        card, body = form_card(parent, "Sleep schedule",
                                "Defines your usable hours each day")
        row = tk.Frame(body, bg='#ffffff')
        row.pack(fill='x')

        self.sleep_bed_var = tk.StringVar(value=self.app.form.sleep['bedtime'])
        self._field_row(row, "Bedtime", self.sleep_bed_var,
                        options=TIME_OPTIONS, combo_width=12)\
            .pack(side=tk.LEFT, padx=(0, 20))

        self.sleep_wake_var = tk.StringVar(value=self.app.form.sleep['wake'])
        self._field_row(row, "Wake time", self.sleep_wake_var,
                        options=TIME_OPTIONS, combo_width=12)\
            .pack(side=tk.LEFT)

    def _form_meals(self, parent):
        card, body = form_card(parent, "Meals",
                                "Anchor points for breakfast, lunch, dinner")
        row = tk.Frame(body, bg='#ffffff')
        row.pack(fill='x')

        self.meals_breakfast_var = tk.StringVar(value=self.app.form.meals['breakfast'])
        self._field_row(row, "Breakfast", self.meals_breakfast_var,
                        options=TIME_OPTIONS, combo_width=11)\
            .pack(side=tk.LEFT, padx=(0, 16))

        self.meals_lunch_var = tk.StringVar(value=self.app.form.meals['lunch'])
        self._field_row(row, "Lunch", self.meals_lunch_var,
                        options=TIME_OPTIONS, combo_width=11)\
            .pack(side=tk.LEFT, padx=(0, 16))

        self.meals_dinner_var = tk.StringVar(value=self.app.form.meals['dinner'])
        self._field_row(row, "Dinner", self.meals_dinner_var,
                        options=TIME_OPTIONS, combo_width=11)\
            .pack(side=tk.LEFT)

    def _form_gym(self, parent):
        card, body = form_card(parent, "Gym / exercise",
                                "We'll fit these around your fixed times")
        row = tk.Frame(body, bg='#ffffff')
        row.pack(fill='x')

        self.gym_times_var = tk.StringVar(value=self.app.form.gym['times'])
        self._field_row(row, "Times per week", self.gym_times_var,
                        options=TIMES_PER_WEEK, combo_width=8)\
            .pack(side=tk.LEFT, padx=(0, 20))

        self.gym_when_var = tk.StringVar(value=self.app.form.gym['when'])
        self._field_row(row, "Preferred time", self.gym_when_var,
                        options=WHEN_OPTIONS, combo_width=12)\
            .pack(side=tk.LEFT, padx=(0, 20))

        self.gym_dur_var = tk.StringVar(value=self.app.form.gym['duration'])
        self._field_row(row, "Duration", self.gym_dur_var,
                        options=DURATION_OPTIONS, combo_width=10)\
            .pack(side=tk.LEFT)

    def _form_study(self, parent):
        card, body = form_card(parent, "Study time",
                                "Blocks of focused study each day")
        row = tk.Frame(body, bg='#ffffff')
        row.pack(fill='x')

        self.study_hours_var = tk.StringVar(value=self.app.form.study['hours'])
        self._field_row(row, "Hours per day", self.study_hours_var,
                        options=STUDY_HOURS, combo_width=10)\
            .pack(side=tk.LEFT, padx=(0, 20))

        self.study_when_var = tk.StringVar(value=self.app.form.study['when'])
        self._field_row(row, "Preferred time", self.study_when_var,
                        options=WHEN_OPTIONS, combo_width=12)\
            .pack(side=tk.LEFT, padx=(0, 20))

        self.study_days_var = tk.StringVar(value=self.app.form.study['days'])
        self._field_row(row, "Which days", self.study_days_var,
                        options=STUDY_DAYS, combo_width=14)\
            .pack(side=tk.LEFT)

    def _form_hobbies(self, parent):
        card, body = form_card(parent, "Hobbies & social", "Time for you")
        row = tk.Frame(body, bg='#ffffff')
        row.pack(fill='x')

        self.hobbies_times_var = tk.StringVar(value=self.app.form.hobbies['times'])
        self._field_row(row, "Times per week", self.hobbies_times_var,
                        options=TIMES_PER_WEEK, combo_width=8)\
            .pack(side=tk.LEFT, padx=(0, 20))

        self.hobbies_when_var = tk.StringVar(value=self.app.form.hobbies['when'])
        self._field_row(row, "Preferred time", self.hobbies_when_var,
                        options=WHEN_OPTIONS, combo_width=12)\
            .pack(side=tk.LEFT, padx=(0, 20))

        self.hobbies_dur_var = tk.StringVar(value=self.app.form.hobbies['duration'])
        self._field_row(row, "Duration", self.hobbies_dur_var,
                        options=DURATION_OPTIONS, combo_width=10)\
            .pack(side=tk.LEFT)

    def _form_errands(self, parent):
        card, body = form_card(parent, "Errands & chores",
                                "Grocery runs, cleaning, admin")
        row = tk.Frame(body, bg='#ffffff')
        row.pack(fill='x')

        self.errands_times_var = tk.StringVar(value=self.app.form.errands['times'])
        self._field_row(row, "Times per week", self.errands_times_var,
                        options=TIMES_PER_WEEK, combo_width=8)\
            .pack(side=tk.LEFT, padx=(0, 20))

        self.errands_when_var = tk.StringVar(value=self.app.form.errands['when'])
        self._field_row(row, "Preferred time", self.errands_when_var,
                        options=WHEN_OPTIONS, combo_width=12)\
            .pack(side=tk.LEFT)

    def _form_other(self, parent):
        card, body = form_card(parent, "Anything else?",
                                "Free-form notes — we'll pass them to the scheduler")
        self.other_text = tk.Text(body, height=4,
                                   font=('Helvetica', 12),
                                   relief='flat',
                                   bg='#f7f7f7', fg='#1a1a1a',
                                   highlightthickness=1,
                                   highlightbackground='#e4e4e4',
                                   highlightcolor='#b01b1b',
                                   padx=12, pady=10, wrap='word')
        self.other_text.pack(fill='x')
        self.other_text.insert('1.0', self.app.form.other)

    # ---- collect ----
    def _remove_row(self, store, row):
        store[:] = [t for t in store if t[0] is not row]
        row.destroy()

    def _collect_from_step2(self):
        f = self.app.form

        f.classes = []
        for (_, name_var, days_h, start_var, dur_var) in getattr(self, '_class_rows', []):
            days = set(days_h._state)
            if not days:
                continue
            f.classes.append({'name': name_var.get().strip(),
                              'days': days,
                              'start': start_var.get(),
                              'duration': dur_var.get()})

        f.work = []
        for (_, days_h, start_var, end_var) in getattr(self, '_work_rows', []):
            days = set(days_h._state)
            if not days:
                continue
            f.work.append({'days': days,
                           'start': start_var.get(),
                           'end': end_var.get()})

        if hasattr(self, 'gym_times_var'):
            f.gym = {'times': self.gym_times_var.get(),
                     'when': self.gym_when_var.get(),
                     'duration': self.gym_dur_var.get()}
        if hasattr(self, 'study_hours_var'):
            f.study = {'hours': self.study_hours_var.get(),
                       'when': self.study_when_var.get(),
                       'days': self.study_days_var.get()}
        if hasattr(self, 'hobbies_times_var'):
            f.hobbies = {'times': self.hobbies_times_var.get(),
                         'when': self.hobbies_when_var.get(),
                         'duration': self.hobbies_dur_var.get()}
        if hasattr(self, 'errands_times_var'):
            f.errands = {'times': self.errands_times_var.get(),
                         'when': self.errands_when_var.get()}
        if hasattr(self, 'meals_breakfast_var'):
            f.meals = {'breakfast': self.meals_breakfast_var.get(),
                       'lunch': self.meals_lunch_var.get(),
                       'dinner': self.meals_dinner_var.get()}
        if hasattr(self, 'sleep_bed_var'):
            f.sleep = {'bedtime': self.sleep_bed_var.get(),
                       'wake': self.sleep_wake_var.get()}
        if hasattr(self, 'other_text'):
            f.other = self.other_text.get('1.0', 'end').strip()

    def _collect_and_review(self):
        self.app._mark_dirty()
        self._collect_from_step2()
        self.show_step(3)

    # =================================================================
    # STEP 3 — REVIEW
    # =================================================================
    def _build_step3(self):
        outer = tk.Frame(self, bg='#ffffff')
        outer.pack(fill=tk.BOTH, expand=True, padx=50, pady=(40, 30))

        header = tk.Frame(outer, bg='#ffffff')
        header.pack(fill=tk.X, pady=(0, 24))

        top_row = tk.Frame(header, bg='#ffffff')
        top_row.pack(fill=tk.X)
        tk.Label(top_row, text=' '.join("REVIEW"),
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg='#b01b1b').pack(side=tk.LEFT)
        tk.Label(top_row, text="STEP 3 OF 3",
                 font=('Helvetica', 9, 'bold'),
                 bg='#ffffff', fg='#cccccc').pack(side=tk.RIGHT)

        tk.Label(header, text="Ready to build?",
                 font=('Helvetica Neue', 28, 'bold'),
                 bg='#ffffff', fg='#1a1a1a').pack(anchor='w', pady=(12, 0))

        tk.Label(header,
                 text="Review what I'll send — then pick from 4 different weekly plans.",
                 font=('Helvetica', 13),
                 bg='#ffffff', fg='#888').pack(anchor='w', pady=(8, 0))

        preview_card = tk.Frame(outer, bg='#fafafa',
                                highlightthickness=1,
                                highlightbackground='#ececec',
                                bd=0)
        preview_card.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(preview_card, bg='#fafafa',
                           highlightthickness=0, bd=0)
        scroll = tk.Scrollbar(preview_card, orient='vertical',
                              command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6), pady=6)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg='#fafafa')
        canvas.create_window((0, 0), window=inner, anchor='nw')

        inner.bind('<Configure>',
                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',
                    lambda e: canvas.itemconfig(1, width=e.width - 6))

        pad = tk.Frame(inner, bg='#fafafa')
        pad.pack(fill=tk.BOTH, expand=True, padx=32, pady=32)

        self._render_preview_sections(pad)

        tk.Frame(pad, bg='#e8e8e8', height=1).pack(fill=tk.X, pady=(20, 20))

        hint = tk.Frame(pad, bg='#fafafa')
        hint.pack(fill=tk.X)
        tk.Label(hint, text="✦",
                 font=('Helvetica', 14),
                 bg='#fafafa', fg='#b01b1b').pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(hint,
                 text="You'll get 4 weekly plans to choose from — Balanced, Morning, Evening, and Compact.",
                 font=('Helvetica', 11),
                 bg='#fafafa', fg='#777',
                 justify='left', anchor='w', wraplength=560)\
            .pack(side=tk.LEFT, fill='x', expand=True)

        footer = tk.Frame(outer, bg='#ffffff')
        footer.pack(fill=tk.X, pady=(24, 0))

        LinkLabel(footer, text="←  Back to edit",
                  command=lambda: self.show_step(2),
                  fg='#888888', hover_fg='#1a1a1a', active_fg='#b01b1b',
                  bg='#ffffff').pack(side=tk.LEFT)

        self.build_btn = AnimatedButton(footer, "Build 4 options",
                                         command=self._build_clicked,
                                         font=('Helvetica Neue', 13, 'bold'),
                                         pad_x=36, pad_y=15)
        self.build_btn.pack(side=tk.RIGHT)

    def _render_preview_sections(self, parent):
        f = self.app.form
        rendered = 0

        def section(icon_key, title, lines):
            nonlocal rendered
            rendered += 1
            self._preview_section(parent, icon_key, title, lines)

        if f.classes:
            lines = []
            for c in f.classes:
                days = '/'.join(s for s in DAYS_SHORT if s in c['days'])
                nm = c['name'] or 'Class'
                lines.append(f"{nm}  ·  {days}  ·  {c['start']}  ·  {c['duration']}")
            section('classes', 'Classes & lectures', lines)

        if f.work:
            lines = []
            for w in f.work:
                days = '/'.join(s for s in DAYS_SHORT if s in w['days'])
                lines.append(f"{days}  ·  {w['start']} – {w['end']}")
            section('work', 'Work / job', lines)

        if 'sleep' in f.categories:
            section('sleep', 'Sleep schedule',
                    [f"{f.sleep['bedtime']} – {f.sleep['wake']}"])

        if 'meals' in f.categories:
            section('meals', 'Meals',
                    [f"Breakfast {f.meals['breakfast']}   ·   "
                     f"Lunch {f.meals['lunch']}   ·   "
                     f"Dinner {f.meals['dinner']}"])

        if 'gym' in f.categories:
            section('gym', 'Gym / exercise',
                    [f"{f.gym['times']}× per week   ·   "
                     f"{f.gym['when']}   ·   "
                     f"{f.gym['duration']} each"])

        if 'study' in f.categories:
            section('study', 'Study time',
                    [f"{f.study['hours']} per day   ·   "
                     f"{f.study['when']}   ·   "
                     f"{f.study['days']}"])

        if 'hobbies' in f.categories:
            section('hobbies', 'Hobbies & social',
                    [f"{f.hobbies['times']}× per week   ·   "
                     f"{f.hobbies['when']}   ·   "
                     f"{f.hobbies['duration']} each"])

        if 'errands' in f.categories:
            section('errands', 'Errands & chores',
                    [f"{f.errands['times']}× per week   ·   "
                     f"{f.errands['when']}"])

        if 'other' in f.categories and f.other.strip():
            words = f.other.strip().split()
            lines, cur = [], ''
            for w in words:
                if len(cur) + len(w) + 1 > 62:
                    lines.append(cur)
                    cur = w
                else:
                    cur = (cur + ' ' + w).strip()
            if cur:
                lines.append(cur)
            section('other', 'Notes', lines)

        if rendered == 0:
            tk.Label(parent,
                     text="Nothing selected — I'll build a generic week.",
                     font=('Helvetica', 12),
                     bg='#fafafa', fg='#999')\
                .pack(pady=60)

    def _preview_section(self, parent, icon_key, title, lines):
        sec = tk.Frame(parent, bg='#fafafa')
        sec.pack(fill='x', pady=(0, 18))

        head = tk.Frame(sec, bg='#fafafa')
        head.pack(fill='x', pady=(0, 8))

        ICON_SIZE = 24
        icon_canvas = tk.Canvas(head, width=ICON_SIZE, height=ICON_SIZE,
                                bg='#fafafa', highlightthickness=0, bd=0)
        icon_canvas.pack(side=tk.LEFT)
        icons.render(icon_canvas, icon_key, ICON_SIZE, bg='#fafafa')

        tk.Label(head, text=title,
                 font=('Helvetica Neue', 13, 'bold'),
                 bg='#fafafa', fg='#1a1a1a').pack(side=tk.LEFT, padx=(12, 0))

        for line in lines:
            row = tk.Frame(sec, bg='#fafafa')
            row.pack(fill='x', pady=2)

            tk.Frame(row, bg='#fafafa', width=ICON_SIZE + 12)\
                .pack(side=tk.LEFT)

            tk.Label(row, text=line,
                     font=('Helvetica', 12),
                     bg='#fafafa', fg='#555',
                     anchor='w', justify='left')\
                .pack(side=tk.LEFT, fill='x', expand=True)

    def _build_clicked(self):
        self.build_btn.set_enabled(False)
        self.build_btn.set_text("Building…")
        self.app.build_variants()

    def build_done(self):
        try:
            self.build_btn.set_enabled(True)
            self.build_btn.set_text("Build 4 options")
        except Exception:
            pass

    def build_error(self, err):
        try:
            self.build_btn.set_enabled(True)
            self.build_btn.set_text("Build 4 options")
        except Exception:
            pass