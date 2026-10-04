# Helpers for turning FormData into prompt strings and preview text.

from config import DAYS_SHORT


def form_to_prompt_data(form):
    fixed_lines = []
    for c in form.classes:
        days = '/'.join(s for s in DAYS_SHORT if s in c['days'])
        nm = c['name'] or 'Class'
        fixed_lines.append(f"  - {nm} on {days} at {c['start']} ({c['duration']})")
    for w in form.work:
        days = '/'.join(s for s in DAYS_SHORT if s in w['days'])
        fixed_lines.append(f"  - Work shift on {days} from {w['start']} to {w['end']}")
    fixed = "\n".join(fixed_lines) or "  (none)"

    flex = []
    if 'gym' in form.categories:
        flex.append(f"  - Gym: {form.gym['times']} times/week, prefer {form.gym['when']}, {form.gym['duration']} each")
    if 'study' in form.categories:
        flex.append(f"  - Study: {form.study['hours']} per day, prefer {form.study['when']}, {form.study['days']}")
    if 'hobbies' in form.categories:
        flex.append(f"  - Hobbies: {form.hobbies['times']} times/week, prefer {form.hobbies['when']}, {form.hobbies['duration']} each")
    if 'errands' in form.categories:
        flex.append(f"  - Errands: {form.errands['times']} times/week, prefer {form.errands['when']}")
    flexible = "\n".join(flex) or "  (none)"

    anchors = []
    if 'sleep' in form.categories:
        anchors.append(f"  - Sleep: {form.sleep['bedtime']} to {form.sleep['wake']}")
    if 'meals' in form.categories:
        anchors.append(f"  - Meals: breakfast {form.meals['breakfast']}, lunch {form.meals['lunch']}, dinner {form.meals['dinner']}")
    anchor_text = "\n".join(anchors) or "  (none)"

    return {
        'fixed':    fixed,
        'flexible': flexible,
        'anchors':  anchor_text,
        'other':    form.other or "(none)",
    }


def form_to_preview_text(form):
    lines = []
    if form.classes:
        lines.append("CLASSES")
        for c in form.classes:
            days = '/'.join(s for s in DAYS_SHORT if s in c['days'])
            nm = c['name'] or 'Class'
            lines.append(f"  • {nm}  ·  {days}  ·  {c['start']}  ({c['duration']})")
        lines.append("")
    if form.work:
        lines.append("WORK")
        for w in form.work:
            days = '/'.join(s for s in DAYS_SHORT if s in w['days'])
            lines.append(f"  • {days}  ·  {w['start']} – {w['end']}")
        lines.append("")
    if 'sleep' in form.categories:
        lines.append("SLEEP")
        lines.append(f"  • {form.sleep['bedtime']} – {form.sleep['wake']}")
        lines.append("")
    if 'meals' in form.categories:
        lines.append("MEALS")
        lines.append(f"  • Breakfast {form.meals['breakfast']}  ·  Lunch {form.meals['lunch']}  ·  Dinner {form.meals['dinner']}")
        lines.append("")
    flex = []
    if 'gym' in form.categories:
        flex.append(f"  • Gym  ·  {form.gym['times']}×/week  ·  {form.gym['when']}  ·  {form.gym['duration']}")
    if 'study' in form.categories:
        flex.append(f"  • Study  ·  {form.study['hours']}/day  ·  {form.study['when']}  ·  {form.study['days']}")
    if 'hobbies' in form.categories:
        flex.append(f"  • Hobbies  ·  {form.hobbies['times']}×/week  ·  {form.hobbies['when']}  ·  {form.hobbies['duration']}")
    if 'errands' in form.categories:
        flex.append(f"  • Errands  ·  {form.errands['times']}×/week  ·  {form.errands['when']}")
    if flex:
        lines.append("FLEXIBLE")
        lines.extend(flex)
        lines.append("")
    if 'other' in form.categories and form.other:
        lines.append("OTHER NOTES")
        lines.append("  " + form.other)
    if not lines:
        lines.append("(No selections — Claude will build a generic week.)")
    return "\n".join(lines)