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
