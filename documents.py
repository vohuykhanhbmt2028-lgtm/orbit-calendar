"""Document I/O — .orbit file format, recents list."""

import os
import json
from datetime import datetime


APP_SUPPORT  = os.path.join(os.path.expanduser('~'),
                             'Library', 'Application Support', 'ORBIT')
RECENTS_PATH = os.path.join(APP_SUPPORT, 'recent.json')
DEFAULT_EXT  = '.orbit'


def ensure_dir():
    os.makedirs(APP_SUPPORT, exist_ok=True)


# ---------------------------------------------------------------------------
# Document I/O
# ---------------------------------------------------------------------------
def save_document(path, payload):
    """Write an .orbit file and add it to recents."""
    ensure_dir()
    payload = dict(payload)
    payload['version'] = 1
    payload['modified'] = datetime.now().isoformat()
    if 'created' not in payload:
        payload['created'] = payload['modified']
    with open(path, 'w') as f:
        json.dump(payload, f, indent=2)
    add_to_recents(path)


def load_document(path):
    with open(path, 'r') as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Recents
# ---------------------------------------------------------------------------
def _read_recents():
    if not os.path.exists(RECENTS_PATH):
        return []
    try:
        with open(RECENTS_PATH, 'r') as f:
            return json.load(f).get('files', [])
    except Exception:
        return []


def _write_recents(files):
    ensure_dir()
    with open(RECENTS_PATH, 'w') as f:
        json.dump({'files': files}, f, indent=2)


def add_to_recents(path):
    path = os.path.abspath(path)
    files = _read_recents()
    files = [f for f in files if f.get('path') != path]
    files.insert(0, {
        'path':   path,
        'name':   os.path.basename(path),
        'opened': datetime.now().isoformat(),
    })
    files = files[:12]
    _write_recents(files)


def get_recents():
    files = _read_recents()
    live = [f for f in files if os.path.exists(f.get('path', ''))]
    if len(live) != len(files):
        _write_recents(live)
    return live


def remove_from_recents(path):
    path = os.path.abspath(path)
    files = _read_recents()
    _write_recents([f for f in files if f.get('path') != path])


def summarize(path):
    """Return (event_count, variant_name) for display in Home."""
    try:
        data = load_document(path)
        schedule = data.get('schedule', {}) or {}
        count = sum(len(v) for v in schedule.values())
        return count, data.get('variant_name', '')
    except Exception:
        return 0, ''