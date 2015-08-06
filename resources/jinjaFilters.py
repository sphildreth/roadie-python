import datetime
import dateutil
from math import floor


def format_age_from_date(value):
    now = datetime.datetime.utcnow()
    now = now.date()
    age = dateutil.relativedelta.relativedelta(now, value)
    return value.strftime("%Y-%m-%d") + " (" + str(age.years) + ")"

def group_release_tracks_filepaths(value):
    try:
        groups = []
        for track in value.Tracks:
            if 'FilePath' in track.Track and track.Track.FilePath not in groups:
                groups.append(track.Track.FilePath)
        return groups
    except:
        return groups
        pass

def calculate_release_discs(value):
    try:
        discs = []
        for track in value.Tracks:
            if track.ReleaseMediaNumber not in discs:
                discs.append(track.ReleaseMediaNumber)
        return len(discs)
    except:
        pass

def calculate_release_tracks_Length(value):
    try:
        result = 0
        for track in value.Tracks:
            if 'Length' in track.Track:
                result += track.Track.Length
        return result
    except:
        pass

def format_tracktime(value):
    return datetime.timedelta(seconds=value)

def format_timedelta(value, time_format="{days} days, {hours2}:{minutes2}:{seconds2}"):
    try:
        if hasattr(value, 'seconds'):
            seconds = value.seconds + value.days * 24 * 3600
        else:
            seconds = int(value)

        seconds_total = seconds

        minutes = int(floor(seconds / 60))
        minutes_total = minutes
        seconds -= minutes * 60

        hours = int(floor(minutes / 60))
        hours_total = hours
        minutes -= hours * 60

        days = int(floor(hours / 24))
        days_total = days
        hours -= days * 24

        years = int(floor(days / 365))
        years_total = years
        days -= years * 365

        return time_format.format(**{
            'seconds': seconds,
            'seconds2': str(seconds).zfill(2),
            'minutes': minutes,
            'minutes2': str(minutes).zfill(2),
            'hours': hours,
            'hours2': str(hours).zfill(2),
            'days': days,
            'years': years,
            'seconds_total': seconds_total,
            'minutes_total': minutes_total,
            'hours_total': hours_total,
            'days_total': days_total,
            'years_total': years_total,
        })
    except:
        pass
