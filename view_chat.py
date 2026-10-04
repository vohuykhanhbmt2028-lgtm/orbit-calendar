import tkinter as tk
from tkinter import scrolledtext
import threading
import json
import re

from ui_helpers import AnimatedButton, LinkLabel


# ---------------------------------------------------------------------------
# JSON extraction (mirrors the helpers in app.py)
# ---------------------------------------------------------------------------
def _extract_json_object(text):
    """Return the outermost balanced JSON object from `text`."""
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
        raise ValueError("No JSON object found")

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
        raise ValueError("Unbalanced JSON braces")

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
# ChatView
# ---------------------------------------------------------------------------
class ChatView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg='#f5f5f5')
        self.app = app
        self.conversation = []
        self.started = False
        self.is_processing = False

        header = tk.Frame(self, bg='#f5f5f5')
        header.pack(fill=tk.X, padx=25, pady=(20, 5))
        tk.Label(header, text="💬  Chat with Claude",
                 font=('Helvetica', 18, 'bold'), bg='#f5f5f5', fg='#222').pack(anchor='w')
        tk.Label(header, text="Describe your week in your own words. Claude will ask questions.",
                 font=('Helvetica', 11), bg='#f5f5f5', fg='#666').pack(anchor='w', pady=(2, 0))

        self.log = scrolledtext.ScrolledText(
            self, wrap='word', font=('Helvetica', 12),
            bg='white', fg='#222', state='disabled',
            relief='flat', bd=0, padx=12, pady=12)
        self.log.pack(fill=tk.BOTH, expand=True, padx=25, pady=(10, 8))
        self.log.tag_configure("you",    foreground='#2980b9', font=('Helvetica', 12, 'bold'))
        self.log.tag_configure("claude", foreground='#8e44ad', font=('Helvetica', 12, 'bold'))

        row = tk.Frame(self, bg='#f5f5f5')
        row.pack(fill=tk.X, padx=25, pady=(0, 5))
        self.entry = tk.Entry(row, font=('Helvetica', 12),
                              bg='white', fg='#222', insertbackground='#222',
                              relief='solid', bd=1)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=8)
        self.entry.bind('<Return>', lambda e: self.send())

        self.send_btn = AnimatedButton(
            row, text="Send  ➤",
            command=self.send,
            font=('Helvetica', 11, 'bold'),
            pad_x=22, pad_y=8)
        self.send_btn.pack(side=tk.RIGHT)

        self.status = tk.Label(self, text="", font=('Helvetica', 9),
                                bg='#f5f5f5', fg='#666')
        self.status.pack(fill=tk.X, padx=25, pady=(0, 10))

        LinkLabel(self, text="←  Back to Setup",
                  command=lambda: self.app.show_setup(),
                  fg='#3498db', hover_fg='#2980b9', active_fg='#1c5980',
                  font=('Helvetica', 11, 'underline'),
                  bg='#f5f5f5').pack(side=tk.LEFT, padx=25, pady=(0, 15))

    # ---------- public ----------
    def ensure_started(self):
        if self.started:
            return
        self.started = True
        self._start()

    def reset(self):
        self.conversation = []
        self.started = False
        self.log.config(state='normal')
        self.log.delete('1.0', tk.END)
        self.log.config(state='disabled')

    # ---------- internals ----------
    def _start(self):
        self.status.config(text="⏳ Starting conversation...")
        self.is_processing = True
        self.send_btn.set_enabled(False)
        self.entry.config(state=tk.DISABLED)
        threading.Thread(target=self._initial_greeting, daemon=True).start()

    def _initial_greeting(self):
        try:
            trigger, greeting = self.app.claude.chat_greeting()
            self.conversation.append(trigger)
            self.conversation.append({"role": "assistant", "content": greeting})
            self.app.root.after(0, self._apply_greeting, greeting, None)
        except Exception as e:
            err_msg = str(e)
            fallback = ("Hello! I'm your scheduling assistant. Tell me about your week — "
                        "classes, work, goals, and any commitments you have.")
            self.conversation.append({"role": "user", "content": "Hi"})
            self.conversation.append({"role": "assistant", "content": fallback})
            self.app.root.after(0, self._apply_greeting, fallback, err_msg)

    def _apply_greeting(self, greeting, err):
        self._add("Claude", greeting)
        self._enable()
        if err:
            self.status.config(text=f"⚠ API error: {err}", fg='#e74c3c')

    def _add(self, sender, text):
        self.log.config(state='normal')
        self.log.insert(tk.END, f"{sender}:  ",
                        ("you" if sender == "You" else "claude",))
        self.log.insert(tk.END, text + "\n\n")
        self.log.config(state='disabled')
        self.log.see(tk.END)

    def _enable(self):
        self.is_processing = False
        self.send_btn.set_enabled(True)
        self.entry.config(state=tk.NORMAL)
        self.entry.focus()
        self.status.config(text="Ready", fg='#666')

    def send(self):
        if self.is_processing:
            return
        txt = self.entry.get().strip()
        if not txt:
            return
        self.entry.delete(0, tk.END)
        self._add("You", txt)
        self.conversation.append({"role": "user", "content": txt})
        self.is_processing = True
        self.send_btn.set_enabled(False)
        self.entry.config(state=tk.DISABLED)
        self.status.config(text="⏳ Thinking...", fg='#FF9800')
        threading.Thread(target=self._call, daemon=True).start()

    def _call(self):
        try:
            reply = self.app.claude.chat_reply(self.conversation)
            self.app.root.after(0, self._add, "Claude", reply)
            if self._has_json(reply):
                self.app.root.after(0, self._extract_schedule, reply)
            self.conversation.append({"role": "assistant", "content": reply})
        except Exception as e:
            err_msg = str(e)
            self.app.root.after(0, self._add, "Claude", f"❌ Error: {err_msg}")
        finally:
            self.app.root.after(0, self._enable)

    @staticmethod
    def _has_json(text):
        try:
            _parse_json_loose(text)
            return True
        except Exception:
            return False

    def _extract_schedule(self, raw):
        try:
            schedule = _parse_json_loose(raw)
            self.app.use_chat_schedule(schedule)
        except Exception as e:
            err_msg = str(e)
            from tkinter import messagebox
            messagebox.showerror("Parse Error", f"Failed to parse schedule:\n{err_msg}")