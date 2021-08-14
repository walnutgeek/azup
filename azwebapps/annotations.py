import re
import typing
from datetime import date, datetime, timedelta

from dateutil.parser import parse as dt_parse


def get_args(cls, default=None):
    if hasattr(cls, "__args__"):
        return cls.__args__
    return default


def is_typing(tt, t, args):
    if args is None:
        args = get_args(t)
    try:
        return t == tt[args]
    except:
        return False


def is_tuple(t, args=None):
    """
    >>> is_tuple(None)
    False
    >>> is_tuple(typing.Optional[int])
    False
    >>> is_tuple(typing.List[int])
    False
    >>> is_tuple(typing.Dict[int,str])
    False
    >>> is_tuple(typing.Tuple[int,str,float])
    True
    >>> is_tuple(typing.Tuple[int])
    True
    """
    return is_typing(typing.Tuple, t, args)


def is_optional(t, args=None):
    """
    >>> n = None
    >>> o = typing.Optional[int]
    >>> l = typing.List[int]
    >>> d = typing.Dict[int,str]
    >>> t3 = typing.Tuple[int,str,float]
    >>> t1 = typing.Tuple[int]
    >>> x=is_optional
    >>> x(n),x(o), x(l), x(d),  x(t3), x(t1)
    (False, True, False, False, False, False)
    >>>
    """
    if args is None:
        args = get_args(t)
    try:
        return t == typing.Optional[args[0]]
    except:
        return False


def is_list(t, args=None):
    """
    >>> n = None
    >>> o = typing.Optional[int]
    >>> l = typing.List[int]
    >>> d = typing.Dict[int,str]
    >>> t3 = typing.Tuple[int,str,float]
    >>> t1 = typing.Tuple[int]
    >>> x=is_list
    >>> x(n), x(o),x(l), x(d),  x(t3), x(t1)
    (False, False, True, False, False, False)
    >>>
    """
    return is_typing(typing.List, t, args)


def is_dict(t, args=None):
    """
    >>> n = None
    >>> o = typing.Optional[int]
    >>> l = typing.List[int]
    >>> d = typing.Dict[int,str]
    >>> t3 = typing.Tuple[int,str,float]
    >>> t1 = typing.Tuple[int]
    >>> x=is_dict
    >>> x(n), x(o), x(l), x(d), x(t3), x(t1)
    (False, False, False, True, False, False)
    >>>
    >>> c = typing.Dict[int,str]
    >>> is_dict(c)
    True
    >>>

    """
    return is_typing(typing.Dict, t, args)


def is_from_typing_module(cls):
    """
    >>> is_from_typing_module(typing.Any)
    True
    >>> is_from_typing_module(typing.Callable[[],typing.IO[bytes]])
    True
    >>> is_from_typing_module(str)
    False
    """
    return cls.__module__ == typing.__name__


def is_classvar(t):
    """
    >>> is_classvar(typing.ClassVar[int])
    True
    >>> is_classvar(int)
    False
    """
    return is_from_typing_module(t) and str(t).startswith("typing.ClassVar[")


def get_attr_hints(o):
    """
    Extracts hints without class variables
    >>> class X:
    ...     x:typing.ClassVar[int]
    ...     y:float
    ...
    >>> get_attr_hints(X)
    {'y': <class 'float'>}
    >>> def abc(x:str, y:int, z:typing.Dict[str,float]) -> bool:
    ...     pass
    ...
    >>> get_attr_hints(abc)
    {'x': <class 'str'>, 'y': <class 'int'>, 'z': typing.Dict[str, float], 'return': <class 'bool'>}

    """
    return {k: h for k, h in typing.get_type_hints(o).items() if not is_classvar(h)}


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


FROM_STR_FACTORIES = {
    timedelta: to_timedelta,
    datetime: dt_parse,
    date: lambda s: dt_parse(s).date(),
}
