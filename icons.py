"""
Hand-drawn category icons for ORBIT.

Each icon is drawn onto a Tk Canvas with consistent stroke weight and
proportions so they read as a coordinated set, not a random collection
of emoji.
"""

import tkinter as tk

INK    = '#1a1a1a'
ACCENT = '#b01b1b'
STROKE = 1.8


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------
def render(canvas, name, size, bg='#fafafa', color=INK, accent=ACCENT):
    fn = _ICONS.get(name)
    if fn is None:
        return
    fn(canvas, size, bg, color, accent)


def _s(size):
    return size / 40.0


# ---------------------------------------------------------------------------
# Individual icons
# ---------------------------------------------------------------------------
def _icon_classes(canvas, size, bg, color, accent):
    s = _s(size)
    # Mortarboard (diamond)
    canvas.create_polygon(
        20*s, 6*s,
        37*s, 15*s,
        20*s, 24*s,
        3*s,  15*s,
        outline=color, fill='', width=STROKE*s, joinstyle='round',
    )
    # Cap base (a shallow arc below the middle)
    canvas.create_arc(
        12*s, 20*s, 28*s, 32*s,
        start=0, extent=-180,
        style='arc', outline=color, width=STROKE*s,
    )
    # Tassel in brand red
    canvas.create_line(
        37*s, 15*s, 37*s, 29*s,
        fill=accent, width=STROKE*s, capstyle='round',
    )
    canvas.create_oval(
        35*s, 28*s, 39*s, 32*s,
        fill=accent, outline=accent,
    )


def _icon_work(canvas, size, bg, color, accent):
    s = _s(size)
    # Body
    canvas.create_rectangle(
        5*s, 14*s, 35*s, 32*s,
        outline=color, fill='', width=STROKE*s,
    )
    # Handle
    canvas.create_arc(
        15*s, 8*s, 25*s, 18*s,
        start=0, extent=180,
        style='arc', outline=color, width=STROKE*s,
    )
    # Divider
    canvas.create_line(
        5*s, 21*s, 35*s, 21*s,
        fill=color, width=STROKE*s * 0.7,
    )
    # Clasp — filled with the card bg so it cuts through the divider
    canvas.create_rectangle(
        17*s, 18*s, 23*s, 24*s,
        fill=bg, outline=color, width=STROKE*s * 0.7,
    )
    canvas.create_line(
        20*s, 20*s, 20*s, 22*s,
        fill=accent, width=STROKE*s * 0.7,
    )


def _icon_sleep(canvas, size, bg, color, accent):
    s = _s(size)
    # Crescent — outer arc + inner arc, connected at the tips
    canvas.create_arc(
        7*s, 7*s, 33*s, 33*s,
        start=45, extent=270,
        style='arc', outline=color, width=STROKE*s,
    )
    # Small sparkle in the upper-right (accent)
    _sparkle(canvas, 31*s, 10*s, 4.5*s, accent)


def _sparkle(canvas, cx, cy, r, color):
    canvas.create_polygon(
        cx, cy - r,
        cx + r * 0.28, cy - r * 0.28,
        cx + r, cy,
        cx + r * 0.28, cy + r * 0.28,
        cx, cy + r,
        cx - r * 0.28, cy + r * 0.28,
        cx - r, cy,
        cx - r * 0.28, cy - r * 0.28,
        fill=color, outline=color,
    )


def _icon_gym(canvas, size, bg, color, accent):
    s = _s(size)
    # Bar
    canvas.create_line(
        12*s, 20*s, 28*s, 20*s,
        fill=color, width=STROKE*s, capstyle='round',
    )
    # Left weights
    canvas.create_rectangle(
        6*s, 12*s, 9*s, 28*s,
        outline=color, fill='', width=STROKE*s,
    )
    canvas.create_rectangle(
        9*s, 15*s, 12*s, 25*s,
        outline=color, fill='', width=STROKE*s,
    )
    # Right weights
    canvas.create_rectangle(
        31*s, 12*s, 34*s, 28*s,
        outline=color, fill='', width=STROKE*s,
    )
    canvas.create_rectangle(
        28*s, 15*s, 31*s, 25*s,
        outline=color, fill='', width=STROKE*s,
    )
    # Red dot on top of the bar
    canvas.create_oval(
        18.5*s, 11*s, 21.5*s, 14*s,
        fill=accent, outline=accent,
    )


def _icon_study(canvas, size, bg, color, accent):
    s = _s(size)
    # Book outline
    canvas.create_rectangle(
        6*s, 10*s, 34*s, 30*s,
        outline=color, fill='', width=STROKE*s,
    )
    # Spine
    canvas.create_line(
        20*s, 10*s, 20*s, 30*s,
        fill=color, width=STROKE*s,
    )
    # Bookmark (accent fill)
    canvas.create_polygon(
        24*s, 10*s,
        28*s, 10*s,
        28*s, 18*s,
        26*s, 16*s,
        24*s, 18*s,
        fill=accent, outline=accent,
    )


def _icon_meals(canvas, size, bg, color, accent):
    s = _s(size)
    # Fork handle
    canvas.create_line(
        11*s, 16*s, 11*s, 32*s,
        fill=color, width=STROKE*s, capstyle='round',
    )
    # Fork tines
    for x in (8, 11, 14):
        canvas.create_line(
            x*s, 8*s, x*s, 16*s,
            fill=color, width=STROKE*s, capstyle='round',
        )
    # Fork joint
    canvas.create_line(
        8*s, 16*s, 14*s, 16*s,
        fill=color, width=STROKE*s,
    )
    # Knife handle
    canvas.create_line(
        29*s, 20*s, 29*s, 32*s,
        fill=color, width=STROKE*s, capstyle='round',
    )
    # Knife blade
    canvas.create_polygon(
        26*s, 8*s,
        32*s, 8*s,
        32*s, 20*s,
        26*s, 20*s,
        outline=color, fill='', width=STROKE*s, joinstyle='round',
    )


def _icon_hobbies(canvas, size, bg, color, accent):
    s = _s(size)
    # Two stems
    canvas.create_line(
        24*s, 10*s, 24*s, 28*s,
        fill=color, width=STROKE*s,
    )
    canvas.create_line(
        14*s, 12*s, 14*s, 30*s,
        fill=color, width=STROKE*s,
    )
    # Connector
    canvas.create_line(
        14*s, 12*s, 24*s, 10*s,
        fill=color, width=STROKE*s,
    )
    # Note heads
    canvas.create_oval(
        9*s, 27*s, 17*s, 33*s,
        fill=color, outline=color,
    )
    canvas.create_oval(
        19*s, 25*s, 27*s, 31*s,
        fill=accent, outline=accent,
    )


def _icon_errands(canvas, size, bg, color, accent):
    s = _s(size)
    # Bag body
    canvas.create_polygon(
        10*s, 14*s,
        30*s, 14*s,
        34*s, 32*s,
        6*s,  32*s,
        outline=color, fill='', width=STROKE*s, joinstyle='round',
    )
    # Handle
    canvas.create_arc(
        14*s, 6*s, 26*s, 20*s,
        start=0, extent=180,
        style='arc', outline=color, width=STROKE*s,
    )
    # Accent dot
    canvas.create_oval(
        19*s, 22*s, 21*s, 24*s,
        fill=accent, outline=accent,
    )


def _icon_other(canvas, size, bg, color, accent):
    s = _s(size)
    # Four-point sparkle
    canvas.create_polygon(
        20*s, 5*s,
        22*s, 18*s,
        35*s, 20*s,
        22*s, 22*s,
        20*s, 35*s,
        18*s, 22*s,
        5*s,  20*s,
        18*s, 18*s,
        fill=color, outline=color,
    )
    # Small accent dot bottom-right
    canvas.create_oval(
        28*s, 28*s, 31*s, 31*s,
        fill=accent, outline=accent,
    )


_ICONS = {
    'classes': _icon_classes,
    'work':    _icon_work,
    'sleep':   _icon_sleep,
    'gym':     _icon_gym,
    'study':   _icon_study,
    'meals':   _icon_meals,
    'hobbies': _icon_hobbies,
    'errands': _icon_errands,
    'other':   _icon_other,
}