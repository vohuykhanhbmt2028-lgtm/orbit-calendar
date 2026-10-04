import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import json
import re
import os
import traceback
from datetime import datetime

from config import ALL_CATEGORIES
from models import FormData
from claude_client import ClaudeClient
from form_utils import form_to_prompt_data
from view_setup import SetupView
from view_variants import VariantsView
from view_calendar import CalendarView
from view_chat import ChatView
from view_splash import SplashView
from view_home import HomeView
import documents


APP_NAME = "ORBIT"
FILE_TYPES = [("ORBIT Calendar", "*.orbit"), ("All files", "*.*")]


# ---------------------------------------------------------------------------
# Robust JSON extraction (unchanged)
# ---------------------------------------------------------------------------
def _extract_json_object(text):
    text = text.strip()
    if text.startswith('```'):
        first_nl = text.find('\n')
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.rstrip().endswith('```'):
            text = text.rstrip()[:-3]
        text = text.strip()

    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found in response")

    depth = 0
    in_string = False
    escape = False
    end = -1
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        raise ValueError("Unbalanced JSON braces in response")
    return text[start:end + 1]


def _repair_json(text):
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return text


def _parse_json_loose(raw):
    json_text = _extract_json_object(raw)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return json.loads(_repair_json(json_text))


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class SchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1200x800")
        self.root.minsize(1050, 650)
        self.root.configure(bg='#f0f0f0')

        # Document state
        self.form = FormData()
        self.variants = []
        self.current_schedule = None
        self.current_variant_name = None
        self.current_file_path = None
        self.is_dirty = False

        self.claude = ClaudeClient()

        self._setup_menu()
        self._setup_container()
        self._setup_status_bar()
        self._build_views()

        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)

        self.show_splash()

        root.bind('<Command-n>', lambda e: self.new_document())
        root.bind('<Command-o>', lambda e: self.open_file())
        root.bind('<Command-s>', lambda e: self.save_file())
        root.bind('<Command-Shift-S>', lambda e: self.save_as_file())
        root.bind('<Command-w>', lambda e: self.close_document())
        root.bind('<Command-1>', lambda e: self.show_home())
        root.bind('<Command-2>', lambda e: self.show_setup())
        root.bind('<Command-3>', lambda e: self.show_calendar())

    # =================================================================
    # Menu
    # =================================================================
    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # App menu
        app_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=APP_NAME, menu=app_menu)
        app_menu.add_command(label=f"About {APP_NAME}", command=self.show_about)
        app_menu.add_separator()
        app_menu.add_command(label="Preferences…", command=self._noop,
                              accelerator="Cmd+,")
        app_menu.add_separator()
        app_menu.add_command(label=f"Hide {APP_NAME}",
                              command=lambda: self.root.tk.call(
                                  '::tk::mac::Hide', None),
                              accelerator="Cmd+H")
        app_menu.add_command(label=f"Quit {APP_NAME}",
                              command=self._on_quit, accelerator="Cmd+Q")

        # File menu (rebuilt each time it opens)
        self.file_menu = tk.Menu(menubar, tearoff=0,
                                  postcommand=self._refresh_file_menu)
        menubar.add_cascade(label="File", menu=self.file_menu)

        # Edit
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Cut",
                              command=lambda: self._focused_event('<<Cut>>'),
                              accelerator="Cmd+X")
        edit_menu.add_command(label="Copy",
                              command=lambda: self._focused_event('<<Copy>>'),
                              accelerator="Cmd+C")
        edit_menu.add_command(label="Paste",
                              command=lambda: self._focused_event('<<Paste>>'),
                              accelerator="Cmd+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All",
                              command=lambda: self._focused_event('<<SelectAll>>'),
                              accelerator="Cmd+A")

        # View
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Home", command=self.show_home, accelerator="Cmd+1")
        view_menu.add_command(label="Setup", command=self.show_setup, accelerator="Cmd+2")
        view_menu.add_command(label="Calendar", command=self.show_calendar, accelerator="Cmd+3")
        view_menu.add_command(label="Chat", command=self.show_chat, accelerator="Cmd+4")

        # Help
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label=f"{APP_NAME} Help", command=self.show_help)

    def _refresh_file_menu(self):
        m = self.file_menu
        m.delete(0, 'end')

        m.add_command(label="New Calendar",
                       command=self.new_document, accelerator="Cmd+N")
        m.add_command(label="Open…",
                       command=self.open_file, accelerator="Cmd+O")

        # Open Recent submenu
        recent_menu = tk.Menu(m, tearoff=0)
        recents = documents.get_recents()
        if recents:
            for entry in recents[:8]:
                path = entry.get('path', '')
                name = entry.get('name', 'Untitled')
                recent_menu.add_command(
                    label=name,
                    command=lambda p=path: self.open_document(p))
            recent_menu.add_separator()
            recent_menu.add_command(label="Clear Menu",
                                     command=self._clear_recents)
        else:
            recent_menu.add_command(label="No Recent Files", state='disabled')
        m.add_cascade(label="Open Recent", menu=recent_menu)

        m.add_separator()
        m.add_command(label="Close",
                       command=self.close_document, accelerator="Cmd+W")
        m.add_command(label="Save",
                       command=self.save_file, accelerator="Cmd+S")
        m.add_command(label="Save As…",
                       command=self.save_as_file, accelerator="Shift+Cmd+S")

    def _clear_recents(self):
        for entry in documents.get_recents():
            documents.remove_from_recents(entry['path'])

    def _noop(self):
        pass

    def _focused_event(self, event_name):
        try:
            w = self.root.focus_get()
            if w:
                w.event_generate(event_name)
        except Exception:
            pass

    # =================================================================
    # Container / status
    # =================================================================
    def _setup_container(self):
        c = tk.Frame(self.root, bg='#f0f0f0')
        c.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        c.grid_rowconfigure(0, weight=1)
        c.grid_columnconfigure(0, weight=1)
        self.container = c

    def _setup_status_bar(self):
        s = tk.Frame(self.root, bg='#e0e0e0', height=24)
        s.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar = tk.Label(s, text="Ready", bg='#e0e0e0', fg='#333', anchor='w')
        self.status_bar.pack(side=tk.LEFT, padx=8)
        self.file_label = tk.Label(s, text="", bg='#e0e0e0', fg='#666', anchor='e')
        self.file_label.pack(side=tk.RIGHT, padx=8)

    def _build_views(self):
        self.views = {
            'splash':   SplashView(self.container, on_done=self._on_splash_done),
            'home':     HomeView(self.container, self),
            'setup':    SetupView(self.container, self),
            'variants': VariantsView(self.container, self),
            'calendar': CalendarView(self.container, self),
            'chat':     ChatView(self.container, self),
        }
        for v in self.views.values():
            v.grid(row=0, column=0, sticky='nsew')

    # =================================================================
    # Views
    # =================================================================
    def show_splash(self):
        self.views['splash'].tkraise()
        self.status_bar.config(text="Loading…")
        self.views['splash'].start()

    def _on_splash_done(self):
        self.show_home()

    def show_home(self):
        self.views['home'].refresh()
        self.views['home'].tkraise()
        self.status_bar.config(text="Home")
        self.file_label.config(text="")
        self._update_title()

    def show_setup(self, step=None):
        self.views['setup'].tkraise()
        if step:
            self.views['setup'].show_step(step)
        self.status_bar.config(text="Setup")

    def show_variants(self):
        if not self.variants:
            self.status_bar.config(text="No variants yet")
            return
        self.views['variants'].render(self.variants)
        self.views['variants'].tkraise()
        self.status_bar.config(text="Pick a variant")

    def show_calendar(self):
        if not self.current_schedule:
            self.status_bar.config(text="No schedule yet")
            return
        self.views['calendar'].display(self.current_schedule,
                                        self.current_variant_name)
        self.views['calendar'].tkraise()
        self.status_bar.config(text="Calendar")

    def show_chat(self):
        self.views['chat'].tkraise()
        self.views['chat'].ensure_started()
        self.status_bar.config(text="Chat")

    # =================================================================
    # Document operations
    # =================================================================
    def new_document(self):
        if not self._prompt_save():
            return
        self._reset_document_state()
        self.show_setup(step=1)
        self.status_bar.config(text="New calendar")
        self._update_title()

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open Calendar",
            filetypes=FILE_TYPES)
        if not path:
            return
        self.open_document(path)

    def open_document(self, path):
        """Open an existing .orbit file directly in the calendar editor."""
        if not self._prompt_save():
            return
        try:
            data = documents.load_document(path)
        except Exception as e:
            messagebox.showerror("Open Error", f"Failed to open:\n{e}")
            return

        # Optional: brief validation
        if not data.get('schedule'):
            messagebox.showwarning(
                "Empty Calendar",
                "This file has no schedule yet. Edit it from the wizard.")
            return

        try:
            import open_calendar
            open_calendar.launch_editor(path)
            self.status_bar.config(
                text=f"Opened {os.path.basename(path)} in editor")
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Could not open editor:\n{e}")

    def close_document(self):
        if not self._prompt_save():
            return
        self._reset_document_state()
        self.show_home()

    def save_file(self):
        if not self.current_file_path:
            self.save_as_file()
            return
        self._write(self.current_file_path)

    def save_as_file(self):
        path = filedialog.asksaveasfilename(
            title="Save Calendar",
            defaultextension=".orbit",
            filetypes=FILE_TYPES)
        if not path:
            return
        self._write(path)
        self.current_file_path = path
        self.file_label.config(text=os.path.basename(path))

    def _write(self, path):
        payload = {
            'form': self._serialize_form(),
            'variants': self.variants,
            'schedule': self.current_schedule,
            'variant_name': self.current_variant_name,
        }
        try:
            documents.save_document(path, payload)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save:\n{e}")
            return

        self.is_dirty = False
        self._sync_calendar_file()
        self.status_bar.config(text=f"Saved {os.path.basename(path)}")
        self._update_title()

    # ---- Form serialization ----
    def _serialize_form(self):
        f = self.form
        return {
            'categories': sorted(f.categories),
            'classes': [{'name': c.get('name', ''),
                         'days': sorted(c.get('days', set())),
                         'start': c.get('start', ''),
                         'duration': c.get('duration', '')}
                        for c in f.classes],
            'work': [{'days': sorted(w.get('days', set())),
                      'start': w.get('start', ''),
                      'end': w.get('end', '')}
                     for w in f.work],
            'gym':     dict(f.gym),
            'study':   dict(f.study),
            'hobbies': dict(f.hobbies),
            'errands': dict(f.errands),
            'meals':   dict(f.meals),
            'sleep':   dict(f.sleep),
            'other':   f.other,
        }

    def _deserialize_form(self, data):
        f = FormData()
        if not data:
            return f
        try:
            f.categories = set(data.get('categories', []))
            f.classes = [{'name': c.get('name', ''),
                          'days': set(c.get('days', [])),
                          'start': c.get('start', '9:00 AM'),
                          'duration': c.get('duration', '1h')}
                         for c in data.get('classes', [])]
            f.work = [{'days': set(w.get('days', [])),
                       'start': w.get('start', '9:00 AM'),
                       'end': w.get('end', '5:00 PM')}
                      for w in data.get('work', [])]
            for key in ('gym', 'study', 'hobbies', 'errands', 'meals', 'sleep'):
                if data.get(key):
                    setattr(f, key, data[key])
            f.other = data.get('other', '')
        except Exception:
            pass
        return f

    def _sync_calendar_file(self):
        """Mirror the schedule to ~/Documents/ORBIT/schedule.json
        so the calendar viewer can pick it up."""
        try:
            orbit_dir = os.path.join(os.path.expanduser('~'),
                                      'Documents', 'ORBIT')
            os.makedirs(orbit_dir, exist_ok=True)
            sched_path = os.path.join(orbit_dir, 'schedule.json')
            payload = {
                'schedule': self.current_schedule or {},
                'variant_name': self.current_variant_name or '',
                'created': datetime.now().isoformat(),
            }
            with open(sched_path, 'w') as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def _reset_document_state(self):
        self.form = FormData()
        self.variants = []
        self.current_schedule = None
        self.current_variant_name = None
        self.current_file_path = None
        self.is_dirty = False
        self.views['chat'].reset()
        self.file_label.config(text="")

    # =================================================================
    # Dirty state
    # =================================================================
    def _mark_dirty(self):
        if not self.is_dirty:
            self.is_dirty = True
            self._update_title()

    def _update_title(self):
        if self.current_file_path:
            name = os.path.basename(self.current_file_path)
        elif self.current_schedule or self.variants or self.form.categories:
            name = "Untitled"
        else:
            self.root.title(APP_NAME)
            return
        prefix = "\u2022 " if self.is_dirty else ""
        self.root.title(f"{prefix}{name} — {APP_NAME}")

    def _prompt_save(self):
        """Return True if safe to proceed, False if cancelled."""
        if not self.is_dirty:
            return True

        name = (os.path.basename(self.current_file_path)
                if self.current_file_path else "Untitled")

        answer = messagebox.askyesnocancel(
            "Unsaved Changes",
            f"Save changes to \u201c{name}\u201d before continuing?")

        if answer is None:
            return False
        if answer is True:
            self.save_file()
            return not self.is_dirty
        return True

    # =================================================================
    # Build variants
    # =================================================================
    def build_variants(self):
        self._mark_dirty()
        data = form_to_prompt_data(self.form)
        self.status_bar.config(text="Sending to Claude…")
        threading.Thread(target=self._build_worker,
                         args=(data,), daemon=True).start()

    def _build_worker(self, data):
        try:
            raw = self.claude.build_variants(**data)
            variants = self._parse_variants(raw)
            self.variants = variants
            self.root.after(0, self._variants_ready)
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda msg=err_msg: self._variants_error(msg))

    @staticmethod
    def _parse_variants(raw):
        obj = _parse_json_loose(raw)
        variants = obj.get('variants') or []
        if not variants:
            raise ValueError("Response contained no variants")
        return variants

    def _variants_ready(self):
        self.views['setup'].build_done()
        self.show_variants()

    def _variants_error(self, err):
        self.views['setup'].build_error(err)
        self.status_bar.config(text="Error building schedule")
        messagebox.showerror("Error", f"Failed to build schedule:\n{err}")

    def regenerate_variants(self):
        self.show_setup(step=3)
        self.views['setup']._build_clicked()

    # =================================================================
    # Pick variant
    # =================================================================
    def pick_variant(self, variant):
        """Stage the variant and show the preview. Does NOT commit."""
        self.current_schedule = variant.get('schedule', {})
        self.current_variant_name = variant.get('name', '')
        self.show_calendar()
        self.status_bar.config(
            text="Preview — commit with \u201cUse this\u201d, or try another variant")

    def use_chat_schedule(self, schedule):
        """Stage the chat-generated schedule. Does NOT commit."""
        self.current_schedule = schedule
        self.current_variant_name = "From chat"
        self.show_calendar()
        self.status_bar.config(
            text="Preview — commit with \u201cUse this\u201d")

    def commit_to_editor(self):
        """Save to a new .orbit file and open the standalone calendar editor."""
        if not self.current_schedule:
            return
        path = self._handoff_to_calendar()
        if not path:
            return
        # Give the editor time to appear, then fade the wizard out
        self._fade_out_and_quit()

    def _fade_out_and_quit(self):
        """Fade the wizard out, then close it."""
        try:
            self.root.attributes('-alpha')
        except Exception:
            self.root.destroy()
            return

        def step(a=1.0):
            a -= 0.12
            if a <= 0:
                self.root.destroy()
                return
            try:
                self.root.attributes('-alpha', a)
            except Exception:
                self.root.destroy()
                return
            self.root.after(25, lambda: step(a))

        self.root.after(200, step)

    def _handoff_to_calendar(self):
        """Write the schedule to a new file, launch the calendar app,
        and return the file path."""
        try:
            # Pick a name — Untitled.orbit, Untitled 2.orbit, ...
            cal_dir = os.path.join(os.path.expanduser('~'),
                                    'Documents', 'ORBIT', 'Calendars')
            os.makedirs(cal_dir, exist_ok=True)

            path = self._next_untitled_path(cal_dir)

            payload = {
                'form': self._serialize_form(),
                'variants': self.variants,
                'schedule': self.current_schedule,
                'variant_name': self.current_variant_name,
            }
            documents.save_document(path, payload)

            # Launch the calendar app
            import open_calendar
            open_calendar.launch_editor(path)

            return path
        except Exception as e:
            traceback.print_exc()          # <-- add this line
            messagebox.showerror("Error", f"Could not open calendar:\n{e}")
            return None

    def _next_untitled_path(self, cal_dir):
        base = os.path.join(cal_dir, 'Untitled.orbit')
        if not os.path.exists(base):
            return base
        i = 2
        while True:
            candidate = os.path.join(cal_dir, f'Untitled {i}.orbit')
            if not os.path.exists(candidate):
                return candidate
            i += 1

    # =================================================================
    # Quit
    # =================================================================
    def _on_quit(self):
        if not self._prompt_save():
            return
        self.root.destroy()

    # =================================================================
    # About / Help
    # =================================================================
    def show_about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME}\n\n"
            "A quiet place to plan your week.\n\n"
            "Built with Python, Tkinter, and Claude AI."
        )

    def show_help(self):
        messagebox.showinfo(
            f"{APP_NAME} Help",
            "Creating a calendar:\n"
            "  1. From Home, click New Calendar.\n"
            "  2. Answer the setup questions.\n"
            "  3. Pick from 4 generated variants.\n"
            "  4. Save with \u2318S.\n\n"
            "Opening an existing calendar:\n"
            "  From Home, click a recent file, or File \u25b8 Open.\n\n"
            "Shortcuts\n"
            "  \u2318N New     \u2318O Open     \u2318S Save     \u21e7\u2318S Save As\n"
            "  \u2318W Close   \u2318Q Quit     \u23181 Home"
        )