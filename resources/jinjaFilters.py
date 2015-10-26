import datetime
import dateutil
import re
from math import floor


def format_age_from_date(value):
    now = datetime.datetime.utcnow()
    now = now.date()
    age = dateutil.relativedelta.relativedelta(now, value)
    return value.strftime("%Y-%m-%d") + " (" + str(age.years) + ")"


def group_release_tracks_filepaths(release):
    groups = []
    try:
        for media in release.media:
            for track in media.tracks:
                if track.filePath and track.filePath not in groups:
                    groups.append(track.filePath)
        return groups
    except:
        return groups
        pass


def count_new_lines(value):
    if not value:
        return 0
    return len(re.findall("\\r", value))


def calculate_release_discs(value):
    try:
        discs = []
        for media in value:
            for track in media.tracks:
                if track.releaseMediaNumber not in discs:
                    discs.append(track.releaseMediaNumber)
        return len(discs)
    except:
        pass


def calculate_release_tracks_Length(value):
    try:
        result = 0
        for media in value.media:
            for track in media.tracks:
                if 'length' in track:
                    result += track.length
        return result
    except:
        pass


def format_tracktime(value):
    return format_timedelta(datetime.timedelta(seconds=int(floor(value / 1000))), "{hours2}:{minutes2}:{seconds2}")


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
