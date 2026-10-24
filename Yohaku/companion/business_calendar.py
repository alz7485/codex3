"""Offline Japanese holidays (2000–2099) and explicit company calendar overrides."""
from datetime import date, timedelta
from functools import lru_cache
import math


@lru_cache(maxsize=100)
def japanese_holidays(year):
    if not 2000 <= year <= 2099:
        return frozenset()
    days = {date(year, m, d) for m, d in ((1,1),(2,11),(4,29),(5,3),(5,5),(11,3),(11,23))}
    def monday(month, nth):
        first = date(year, month, 1)
        return first + timedelta(days=(7-first.weekday()) % 7 + 7*(nth-1))
    days.add(monday(1, 2))
    days.add(date(year, 3, int(20.8431 + .242194*(year-1980) - math.floor((year-1980)/4))))
    days.add(date(year, 9, int(23.2488 + .242194*(year-1980) - math.floor((year-1980)/4))))
    days.add(monday(9, 3) if year >= 2003 else date(year, 9, 15))
    if year <= 2018: days.add(date(year, 12, 23))
    if year >= 2020: days.add(date(year, 2, 23))
    if year >= 2007: days.add(date(year, 5, 4))
    if year == 2020:
        days.update((date(year,7,23),date(year,7,24),date(year,8,10)))
    elif year == 2021:
        days.update((date(year,7,22),date(year,7,23),date(year,8,8)))
    else:
        days.add(monday(7,3) if year >= 2003 else date(year,7,20))
        days.add(monday(10,2))
        if year >= 2016: days.add(date(year,8,11))
    if year == 2019: days.update((date(year,5,1),date(year,10,22)))
    national = set(days)
    for day in sorted(national):
        between = day + timedelta(days=1)
        if between.weekday() != 6 and between + timedelta(days=1) in national:
            days.add(between)
    for day in sorted(national):
        if day.weekday() == 6:
            substitute = day + timedelta(days=1)
            if year >= 2007:
                while substitute in days: substitute += timedelta(days=1)
            days.add(substitute)
    return frozenset(days)


class BusinessCalendar:
    def __init__(self, options=None):
        options = options or {}
        self.weekdays = set(options.get('weekdays', range(5)))
        self.holidays = set(options.get('holidays', ()))
        self.workdays = set(options.get('workdays', ()))
        self.japanese = options.get('japanese_holidays', True)

    def is_business_day(self, day):
        if day.isoformat() in self.workdays: return True
        return (day.weekday() in self.weekdays and day.isoformat() not in self.holidays
                and not (self.japanese and day in japanese_holidays(day.year)))
