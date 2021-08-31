import inspect
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple, Type, Union

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
    >>> x=to_timedelta("1Y1D"); (x.days,x.seconds)
    (366, 21600)
    >>> x=to_timedelta("1Y 1D"); (x.days,x.seconds)
    (366, 21600)
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


def filter_options(ll: Iterable[str]) -> Tuple[List[str], Dict[str, Any]]:
    """
    >>> filter_options(["a","-a","-b:a"])
    (['a'], {'a': True, 'b': 'a'})
    >>>
    """
    filtered = []
    options: Dict[str, Any] = {}
    for l in ll:
        if l.startswith("-"):
            split = l[1:].split(":", 2)
            if len(split) == 1:
                options[split[0]] = True
            else:
                options[split[0]] = split[1]
        else:
            filtered.append(l)
    return filtered, options


class CliActions:
    def __init__(self, script=sys.argv[0]):
        if "-m" == script:
            script = __name__
        else:
            script = Path(script).name
        cls = type(self)
        self._actions = [f for f in dir(cls) if not f.startswith("_")]
        h = []
        h.append("\nUSAGES:")
        for a in self._actions:
            fn = getattr(cls, a)
            names, _, _, defaults = inspect.getfullargspec(fn)[:4]
            if defaults is None:
                defaults = ()
            def_offset = len(names) - len(defaults)
            optonals = {k: v for k, v in zip(names[def_offset:], defaults)}
            a_args = " ".join(
                f"[{n}]" if n in optonals else f"<{n}>" for n in names[1:]
            )
            h.append(f" {script} {a} {a_args}")
        h.append("")
        self._show_help = False
        self._help = "\n".join(h)

    def _check_action(self, act):
        if act in self._actions:
            return True
        else:
            self._help = f"{act} is not valid action\n" + self._help
            self._show_help = True
            return False

    def _invoke(self, *args):
        if not self._show_help:
            act = args[0]
            if self._check_action(act):
                return getattr(self, act)(*args[1:])
        return ""


def replace_all(replacements: Dict[str, str], text: str) -> str:
    """
    >>> replace_all({"ab":"xy", "zy": "qtx", "yz": "x", "xml": ""}, "yzk ab zy ab k")
    'xk xy qtx xy k'

    """
    for k, v in replacements.items():
        pos = 0
        while True:
            try:
                new_pos = text.index(k, pos)
                text = text[:new_pos] + v + text[new_pos + len(k) :]
                pos = new_pos + len(v)
            except ValueError:
                break
    return text


class Secrets:
    vals: Dict[str, str] = {}
    keys: Dict[str, str] = {}

    def add(self, prefix: str, value: str):
        idx = 1
        if value in self.keys:
            return self.keys[value]
        while True:
            nk = f"{prefix}_{idx:03d}"
            if nk not in self.vals:
                self.vals = {nk: value, **self.vals}
                self.keys = {value: nk, **self.keys}
                return nk
            idx += 1

    def show(self, text: str):
        return replace_all(self.vals, text)

    def hide(self, text: str):
        return replace_all(self.keys, text)
