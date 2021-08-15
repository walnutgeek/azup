import re
from datetime import date, datetime, timedelta
from typing import Callable, Dict, Type

from dateutil.parser import parse as dt_parse


def guess_location_from_display_name(display_name):
    """
    >>> guess_location_from_display_name("UAE Central")
    'uaecentral'
    >>> guess_location_from_display_name("Southeast Asia (Stage)")
    'southeastasiastage'
    """
    return re.sub(r"[\s()]+", "", display_name).lower()


def to_snake_case(name):
    """
    >>> list(map(to_snake_case,['Content-Length', 'Content-Length', 'CreationTime','LastAccessTime', 'LastWriteTime', 'Etag']))
    ['content_length', 'content_length', 'creation_time', 'last_access_time', 'last_write_time', 'etag']
    """
    return re.sub("([a-z0-9])[-_]?([A-Z])", r"\1_\2", name).lower()


SECONDS_IN_DAY = 60 * 60 * 24
INTERVALS = {
    "Y": 365.25 * SECONDS_IN_DAY,
    "M": 30.4375,
    "W": 7 * SECONDS_IN_DAY,
    "D": SECONDS_IN_DAY,
    "h": 60 * 60,
    "m": 60,
    "s": 1,
}


def to_timedelta(s: str) -> timedelta:
    """
    >>> to_timedelta("1Y1D")
    datetime.timedelta(days=366, seconds=21600)
    >>> to_timedelta("1Y 1D")
    datetime.timedelta(days=366, seconds=21600)
    """
    return timedelta(
        seconds=sum(
            int(t[:-1]) * INTERVALS[t[-1]]
            for t in re.sub(r"[\s_-]*(\d+)", r" \1", s).split()
            if t
        )
    )


FROM_STR_FACTORIES: Dict[Type, Callable] = {
    timedelta: to_timedelta,
    datetime: dt_parse,
    date: lambda s: dt_parse(s).date(),
}
