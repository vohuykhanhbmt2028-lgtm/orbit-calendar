# Data model for the user's form input.

class FormData:
    def __init__(self):
        self.categories = set()
        self.classes = [{'name': '', 'days': set(), 'start': '9:00 AM', 'duration': '1h'}]
        self.work    = [{'days': set(), 'start': '9:00 AM', 'end': '5:00 PM'}]
        self.gym     = {'times': '3', 'when': 'Morning', 'duration': '1h'}
        self.study   = {'hours': '2h', 'when': 'Evening', 'days': 'All days'}
        self.hobbies = {'times': '2', 'when': 'Evening', 'duration': '2h'}
        self.errands = {'times': '2', 'when': 'Afternoon'}
        self.meals   = {'breakfast': '8:00 AM', 'lunch': '12:00 PM', 'dinner': '6:00 PM'}
        self.sleep   = {'bedtime': '11:00 PM', 'wake': '7:00 AM'}
        self.other   = ''