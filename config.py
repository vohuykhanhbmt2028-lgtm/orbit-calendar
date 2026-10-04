# Constant values — days, times, categories.

DAYS_SHORT = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su']
DAYS_FULL  = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DAY_MAP    = dict(zip(DAYS_SHORT, DAYS_FULL))

TIME_OPTIONS = (
    [f"{h}:00 AM" for h in range(6, 12)] +
    ["12:00 PM"] +
    [f"{h}:00 PM" for h in range(1, 12)] +
    ["12:00 AM"]
)
DURATION_OPTIONS = ['30m', '45m', '1h', '1.5h', '2h', '3h']
TIMES_PER_WEEK   = ['1', '2', '3', '4', '5', '6', '7']
WHEN_OPTIONS     = ['Morning', 'Midday', 'Afternoon', 'Evening', 'Any time']
STUDY_DAYS       = ['All days', 'Weekdays only', 'Weekends only']
STUDY_HOURS      = ['1h', '2h', '3h', '4h', '5h']

# The 4 categories always shown on the first screen.
CORE_CATEGORIES = [
    ('classes', 'Classes & lectures', 'Fixed times — days, start time, duration'),
    ('work',    'Work / job',          'Fixed shifts'),
    ('sleep',   'Sleep schedule',      'Defines your waking hours'),
    ('gym',     'Gym / exercise',      'Flexible — we place it for you'),
]

EXTRA_CATEGORIES = [
    ('study',   'Study time',          'Flexible study blocks'),
    ('meals',   'Meals',               'Anchors for breakfast, lunch, dinner'),
    ('hobbies', 'Hobbies & social',    'Flexible, for fun'),
    ('errands', 'Errands & chores',    'Flexible, as needed'),
    ('other',   'Something else',      'Anything the boxes missed'),
]

ALL_CATEGORIES = CORE_CATEGORIES + EXTRA_CATEGORIES

ALL_CATEGORIES = CORE_CATEGORIES + EXTRA_CATEGORIES