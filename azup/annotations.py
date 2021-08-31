import typing


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
