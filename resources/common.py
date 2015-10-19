import datetime
import unicodedata
import string
import arrow
from string import ascii_letters, digits
import sys


def isEqual(s1, s2):
    """ Method that takes two strings and returns True or False, based
        on if they are equal, regardless of case."""
    c1 = s1 or ''
    c2 = s2 or ''
    return c1.lower().strip() == c2.lower().strip()


def isInList(list, s1):
    """See if given value is in the list"""
    c1 = s1 or ''
    if not list:
        return False
    if isinstance(list, dict):
        return c1.lower().strip() in list
    return [l for l in list if isEqual(l, s1)]


def parseDate(date):
    """
    Parse the given date string into a Date object
    :type date: str
    """
    if not date:
        return None
    if isinstance(date, (datetime.date, datetime.datetime)):
        date = date.isoformat()
    result = None
    yearFormat = "YYYY"
    dateFormat = "YYYY-MM-DD"
    if len(date) == 4:
        dateFormat = yearFormat
    elif len(date) == 7:
        dateFormat = "YYYY-MM"
    elif len(date) != 10:
        dateFormat = yearFormat
    if not dateFormat:
        return result
    try:
        result = arrow.get(date, dateFormat).date()
    except:
        pass
    return result


def deriveArtistFromName(name):
    """
    Ensure that the given name doesnt have usual suspects like "Featuring" or "Ft" or " with" to attempt to return just
    the artist name

    :param name: str
    :return: str
    """
    if not name:
        return name
    removeParts = [" ft. ", " ft ", " feat ", " feat. "]
    for removePart in removeParts:
        i = name.lower().find(removePart)
        if i > -1:
            name = name[:i]
    return string.capwords(name)


def createCleanedName(name):
    """
    Take the given name and strip out everything not alphanumeric for saving as a potential alternate name
    :param name: str
    :return: str
    """
    name = name.lower().replace("&", "and")
    return "".join([ch for ch in name if ch in (ascii_letters + digits)])


def uprint(*objects, sep=' ', end='\n', file=sys.stdout):
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file)
    else:
        f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
        print(*map(f, objects), sep=sep, end=end, file=file)
