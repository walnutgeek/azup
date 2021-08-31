from typing import Any, Callable, Dict, Iterable, Type

import yaml
from yaml.loader import SafeLoader

from azup.annotations import (
    get_args,
    get_attr_hints,
    is_dict,
    is_from_typing_module,
    is_list,
)


def build_factory_dict(yamlables: Iterable[Type]) -> Dict[Type, Callable]:
    return {cls: cls.from_dict for cls in yamlables}  # type:ignore


def load_from_file(f, root: "CtxPath", cls: Type):
    with open(f) as fp:
        return cls.from_dict(root, yaml.load(fp, Loader=SafeLoader))  # type:ignore


def setattrs_from_dict(o: Any, path: "CtxPath", d: Dict[str, Any]):
    hints = get_attr_hints(type(o))
    for k in d.keys():
        if k not in hints:
            raise ValueError(f"{k} not in {hints}")
        v = cast_to_type(hints[k], path.child(k), d[k])
        setattr(o, k, v)
    return o


def cast_to_type(cls, path: "CtxPath", in_v):
    if in_v is None:
        return None
    in_cls = type(in_v)
    if cls == in_cls:
        return in_v

    elif in_cls == str:
        if cls in path.ctx.str_factories:
            return path.ctx.str_factories[cls](in_v)
        else:
            return cls(in_v)
    elif is_from_typing_module(cls):
        args = get_args(cls, [])
        if is_dict(cls, args):
            return {
                child_k: cast_to_type(args[1], path.child(child_k), in_v[child_k])
                for child_k in in_v
            }
        elif is_list(cls, args):
            return [
                cast_to_type(args[0], path.child(str(idx)), v)
                for idx, v in enumerate(in_v)
            ]
    elif in_cls == dict:
        if cls in path.ctx.dict_factories:
            factory = path.ctx.dict_factories[cls]
            return factory(path, in_v)
        else:
            return cls(in_v)


def to_dict(o: Any, yamlables: Iterable[Type]) -> Dict[str, Any]:
    yamlables_set = set(yamlables)
    yamlables_cache = {t: t for t in yamlables_set}

    def downcast_type(t):
        if t in yamlables_cache:
            return yamlables_cache[t]
        for st in yamlables_set:
            if issubclass(t, st):
                yamlables_cache[t] = st
                return st
        return t

    def cvt_attr(c, cls):
        if is_from_typing_module(cls):
            args = get_args(cls, [])
            if is_dict(cls, args):
                return {k: convert(c[k]) for k in c}
            elif is_list(cls, args):
                return [convert(v) for v in c]
        elif cls in (str, int, bool, float) or c is None:
            return c
        else:
            return convert(c)
        raise AssertionError(f"not sure what to do {c} {cls}")

    def convert(o):
        t = downcast_type(type(o))
        hints = get_attr_hints(t)
        if isinstance(o, ContextAware):
            del hints["path"]
            if "name" in hints:
                del hints["name"]
        out = {}
        for n in hints:
            if hasattr(o, n):
                c = getattr(o, n)
                cls = hints[n]
                out[n] = cvt_attr(c, cls)
        return out

    return convert(o)


def to_yaml(o, yamlables: Iterable[Type]):
    return yaml.safe_dump(to_dict(o, yamlables))


from azup.context import ContextAware, CtxPath
