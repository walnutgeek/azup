import typing
from azwebapps.annotations import FROM_STR_FACTORIES, get_attr_hints, is_from_typing_module, get_args, is_dict, is_list

class Context:
    config:"ContextAware"
    state:"ContextAware"

    def root(self):
        return CtxPath(self)


class CtxPath:
    ctx: Context
    parts: typing.Tuple[str,...]

    def __init__(self, ctx:Context, *parts:str):
        self.ctx = ctx
        self.parts = tuple(parts)
    
    def parent(self, generation =1):
        return CtxPath(self.ctx, *self.parts[:-getration])
    
    def child(self, *parts:str):
        return CtxPath(self.ctx, *self.parts, *parts)

    def key(self):
        return self.parts[-1]

    def all_keys(self):
        pp = self.parent()
        keys = set(pp.get_config().keys())
        keys.update(pp.get_state().keys())
        return keys

    def get_state(self)->typing.Any:
        return self._walk_the_path(self.ctx.state)

    def get_config(self)->typing.Any:
        return self._walk_the_path(self.ctx.config)

    def is_root(self)->bool:
        return len(self.parts) == 0 

    def _walk_the_path(self, x:typing.Any)->typing.Any:
        if self.is_root():
            return x
        else:
            end = len(self.parts)
            i = 1
            for i in range(0, end, 2):
                x = getattr(x, self.parts[i])
                i += 1
                if i < end:
                    x = x[self.parts[i]]
                else:
                    break
            return x


class ContextAware:
    path: CtxPath
    
    def __init__(self, path:CtxPath):
        self.path = path


def setattrs_from_dict( 
    o:typing.Any, 
    path:CtxPath,
    d:typing.Dict[str,typing.Any],
    from_str_factories=FROM_STR_FACTORIES,
    from_dict_factories={}):
    hints = get_attr_hints(type(o))
    for k in d.keys():
        if k not in hints:
            raise ValueError(f"{k} not in {hints}")
        v = cast_to_type(hints[k], path.child(k), d[k], from_str_factories, from_dict_factories)
        setattr(o, k, v)
    return o


def cast_to_type(
    cls, 
    path:CtxPath, 
    in_v, 
    from_str_factories=FROM_STR_FACTORIES,
    from_dict_factories={}):
    """ """
    if in_v is None:
        return None
    in_cls = type(in_v)
    if cls == in_cls:
        return in_v
    
    elif in_cls == str:
        if cls in from_str_factories:
            return from_str_factories[cls](in_v)
        else : 
            return cls(in_v)
    elif is_from_typing_module(cls):
        args = get_args(cls, [])
        if is_dict(cls, args):
            return {
                child_k : cast_to_type(args[1], path.child(child_k), in_v[child_k], from_str_factories, from_dict_factories) 
                for child_k in in_v
                }
        elif is_list(cls, args):
            return [
                cast_to_type(args[1], path.child(str(idx)), v, from_str_factories, from_dict_factories) 
                for idx, v in enumerate(in_v)
                ]
    elif in_cls == dict:
        if cls in from_dict_factories:
            factory = from_dict_factories[cls]
            if 'path' in get_attr_hints(factory):
                return factory(path, in_v)
            else:
                return factory(in_v)
        else:
            return cls(in_v)
