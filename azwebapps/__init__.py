import re
import sys
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Tuple, Type, Union

from dateutil.parser import parse as dt_parse


def cleanup_misc_chars(display_name):
    """
    >>> cleanup_misc_chars("UAE Central")
    'uaecentral'
    >>> cleanup_misc_chars("Southeast Asia (Stage)")
    'southeastasiastage'
    >>> cleanup_misc_chars("--hyper-v")
    'hyperv'
    >>> cleanup_misc_chars("--is-linux")
    'islinux'
    """
    return re.sub(r"[\s()\-_'\"]+", "", display_name).lower()


def educated_guess(value: str, choices: Union[Dict[str, List[str]], List[str]]) -> str:
    """
    >>> educated_guess('HyperV' ,['--is-linux','--hyper-v'])
    '--hyper-v'
    >>> educated_guess('hyper' ,['--is-linux','--hyper-v'])
    '--hyper-v'
    >>> educated_guess('h' ,['--is-linux','--hyper-v'])
    '--hyper-v'
    >>> educated_guess('LINUX' ,['--is-linux','--hyper-v'])
    '--is-linux'
    >>> educated_guess('l' ,['--hyper-v','--is-linux'])
    '--is-linux'
    >>> educated_guess('' ,['--is-linux','--hyper-v'])
    '--is-linux'
    >>> educated_guess('' ,['--hyper-v','--is-linux'])
    '--hyper-v'
    >>> educated_guess('l' ,{'--is-linux':[],'--hyper-v':['app']})
    '--is-linux'
    >>> educated_guess('h' ,{'--is-linux':[],'--hyper-v':['app']})
    '--hyper-v'
    >>> educated_guess('app' ,{'--is-linux':[], '--hyper-v':[], '':['app']})
    ''
    >>>
    """
    clean_val = cleanup_misc_chars(value)
    clean_choices: List[Tuple[int, str]] = []
    if isinstance(choices, dict):
        tmp_choices = []
        for k in choices:
            tmp_choices.append(k)
            clean_choices.append((len(clean_choices), cleanup_misc_chars(k)))
            for synonym in choices[k]:
                tmp_choices.append(k)
                clean_choices.append((len(clean_choices), cleanup_misc_chars(synonym)))
        choices = tmp_choices
    else:
        clean_choices = list(enumerate(list(map(cleanup_misc_chars, choices))))
    for i, v in clean_choices:
        if clean_val == v:
            return choices[i]
    if clean_val:
        for i, v in clean_choices:
            if clean_val in v:
                return choices[i]
    return choices[0]


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


def dt_iso_parse(s):
    return dt_parse(s).replace(tzinfo=None)


FROM_STR_FACTORIES: Dict[Type, Callable] = {
    timedelta: to_timedelta,
    datetime: dt_parse,
    date: lambda s: dt_parse(s).date(),
}


def print_err(*args):
    print(*args, file=sys.stderr)


def mount_to_id(mount_dir):
    """
    >>> mount_to_id("/d4")
    '_d4'
    """
    return mount_dir.replace("/", "_")
