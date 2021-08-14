import typing
from datetime import datetime, timedelta

import yaml
from dateutil.parser import parse as dt_parse
from yaml.loader import SafeLoader

import azwebapps
from azwebapps.annotations import (
    FROM_STR_FACTORIES,
    get_args,
    get_attr_hints,
    is_dict,
    is_from_typing_module,
    is_list,
)


class CtxPath:
    ctx: "Context"
    parts: typing.Tuple[str, ...]

    def __init__(self, ctx: "Context", *parts: str):
        self.ctx = ctx
        self.parts = tuple(parts)

    def parent(self, generation=1) -> "CtxPath":
        return CtxPath(self.ctx, *self.parts[:-generation])

    def child(self, *parts: str) -> "CtxPath":
        return CtxPath(self.ctx, *self.parts, *parts)

    def absolute(self, *parts: str) -> "CtxPath":
        return CtxPath(self.ctx, *parts)

    def key(self) -> str:
        return self.parts[-1]

    def all_keys(self):
        pp = self.parent()
        keys = set(pp.get_config().keys())
        keys.update(pp.get_state().keys())
        return keys

    def get_state(self) -> typing.Any:
        return self._walk_the_path(self.ctx.state)

    def get_config(self) -> typing.Any:
        return self._walk_the_path(self.ctx.config)

    def is_root(self) -> bool:
        return len(self.parts) == 0

    def _walk_the_path(self, x: typing.Any) -> typing.Any:
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

    def __str__(self):
        return " > ".join(self.parts)


class ContextAware:
    path: CtxPath

    def __init__(self, path: CtxPath):
        self.path = path

    @classmethod
    def build(cls, parent: "ContextAware", *parts: str) -> typing.Any:
        return cls(parent.path.child(*parts))

    @classmethod
    def from_dict(cls, path: CtxPath, d: typing.Dict[str, typing.Any]):
        o = cls(path)
        if not path.is_root():
            o.name = path.key()  # type:ignore
        setattrs_from_dict(o, path, d, from_dict_factories=o.path.ctx.dict_factories)
        return o

    def update(self, **props):
        for k, v in props.items():
            setattr(self, k, v)
        return self


def setattrs_from_dict(
    o: typing.Any,
    path: CtxPath,
    d: typing.Dict[str, typing.Any],
    from_str_factories=FROM_STR_FACTORIES,
    from_dict_factories={},
):
    hints = get_attr_hints(type(o))
    for k in d.keys():
        if k not in hints:
            raise ValueError(f"{k} not in {hints}")
        v = cast_to_type(
            hints[k],
            None if path is None else path.child(k),
            d[k],
            from_str_factories,
            from_dict_factories,
        )
        setattr(o, k, v)
    return o


def cast_to_type(
    cls,
    path: CtxPath,
    in_v,
    from_str_factories=FROM_STR_FACTORIES,
    from_dict_factories={},
):
    """ """
    if in_v is None:
        return None
    in_cls = type(in_v)
    if cls == in_cls:
        return in_v

    elif in_cls == str:
        if cls in from_str_factories:
            return from_str_factories[cls](in_v)
        else:
            return cls(in_v)
    elif is_from_typing_module(cls):
        args = get_args(cls, [])
        if is_dict(cls, args):
            return {
                child_k: cast_to_type(
                    args[1],
                    path.child(child_k),
                    in_v[child_k],
                    from_str_factories,
                    from_dict_factories,
                )
                for child_k in in_v
            }
        elif is_list(cls, args):
            return [
                cast_to_type(
                    args[1],
                    path.child(str(idx)),
                    v,
                    from_str_factories,
                    from_dict_factories,
                )
                for idx, v in enumerate(in_v)
            ]
    elif in_cls == dict:
        if cls in from_dict_factories:
            factory = from_dict_factories[cls]
            if "path" in get_attr_hints(factory):
                return factory(path, in_v)
            else:
                return factory(in_v)
        else:
            return cls(in_v)


# storage


class FileShare(ContextAware):
    name: str
    quota: int
    key_used: int


class Storage(ContextAware):
    name: str
    shares: typing.Dict[str, FileShare]


# container image repo


class Repository(ContextAware):
    name: str
    purge_after: timedelta

    def url(self):
        acr: Acr = self.path.parent(2).get_config()
        return f"{acr.name}.azurecr.io/{acr.name}/{self.name}"


class Acr(ContextAware):
    name: str
    repos: typing.Dict[str, Repository]


# app services


class Mount(ContextAware):
    name: str
    account: str
    share: str

    def default_custom_id(self):
        return self.name.replace("/", "_")

    def access_key(self):
        acc_path = self.path.absolute("storages", self.name)
        fs: FileShare = acc_path.child("shares", self.share).get_config()
        storage: StorageState = acc_path.get_state()
        return storage.get_keys()[fs.key_used]


class Container:
    acr: str
    repo: str
    tag: str

    @classmethod
    def from_dict(cls, d: typing.Dict[str, typing.Any]) -> "Container":
        return setattrs_from_dict(cls(), None, d, from_dict_factories=CONFIG_FACTORIES)

    @classmethod
    def parse(cls, docker_spec: str) -> "Container":
        o = cls()
        _, o.acr, rest = docker_spec.split("|")[1].split("/")
        o.repo, o.tag = rest.split(":")
        return o


class Service(ContextAware):
    name: str
    container: Container
    mounts: typing.Dict[str, Mount]


class AppServicePlan(ContextAware):
    name: str
    sku: str
    kind: str
    location: str
    services: typing.Dict[str, Service]


# root config


class WebServicesConfig(ContextAware):
    group: str
    storages: typing.Dict[str, Storage]
    plans: typing.Dict[str, AppServicePlan]
    acrs: typing.Dict[str, Acr]


CONFIG_FACTORIES = {
    cls: cls.from_dict  # type:ignore
    for cls in (
        WebServicesConfig,
        Repository,
        Service,
        AppServicePlan,
        Container,
        Storage,
        Acr,
        FileShare,
        Mount,
    )
}


def load_config(root: CtxPath, f):
    with open(f) as fp:
        return WebServicesConfig.from_dict(root, yaml.load(fp, Loader=SafeLoader))


class ImageVer:
    def __init__(self, repo_path: CtxPath, d: typing.Dict[str, typing.Any]):
        self.repo_path = repo_path
        self.digest = d["digest"]
        self.timestamp = dt_parse(d["timestamp"]).replace(tzinfo=None)
        self.tags = []
        self.git = None
        for t in d["tags"]:
            if len(t) == 40:
                self.git = t
            else:
                self.tags.append(t)

    def __str__(self):
        return f"{self.digest} {self.timestamp} {self.git} {self.tags}"

    def __repr__(self):
        return str(self)


class RepoState(Repository):
    vers: typing.List[ImageVer]
    by_tag: typing.Dict[str, ImageVer]

    def load(self, acr: "AcrState"):
        az_cmd = self.path.ctx.az_cmd
        self.name = self.path.key()
        self.vers = [ImageVer(self.path, v) for v in (az_cmd.show_manifests(self, acr))]
        self.by_tag = {}
        for iv in self.vers:
            if iv.tags:
                for tag in iv.tags:
                    self.by_tag[tag] = iv

    def to_remove(self, now: datetime = None) -> typing.List[ImageVer]:
        if not now:
            now = datetime.utcnow()
        repo: Repository = self.path.get_config()
        cutoff = now - repo.purge_after
        return [iv for iv in self.vers if iv.timestamp < cutoff]


class AcrState(Acr):
    def load(self) -> "AcrState":
        az_cmd = self.path.ctx.az_cmd
        self.name = self.path.key()
        self.repos = {
            n: RepoState.build(self, "repos", n).load(self)
            for n in az_cmd.get_acr_repo_list(self)
        }
        return self


class FileShareState(FileShare):
    def load(self, d: typing.Dict[str, typing.Any]):
        self.name = self.path.key()
        self.quota = d["properties"]["quota"]


class StorageState(Storage):
    access_tier: str

    def load(self, d: typing.Dict[str, typing.Any]):
        az_cmd = self.path.ctx.az_cmd
        self.name = self.path.key()
        self.access_tier = d["accessTier"]
        self.shares = {
            d["name"]: FileShareState.build(self, "shares", d["name"]).load(d)
            for d in az_cmd.list_file_shares(self)
        }

    def get_keys(self) -> typing.List[str]:
        az_cmd = self.path.ctx.az_cmd
        return [d["value"] for d in az_cmd.list_storage_keys(self)]


class MountState(Mount):
    state: str

    def load(self, d: typing.Dict[str, typing.Any]) -> "MountState":
        self.name = self.path.key()
        self.custom_id = d["name"]
        self.state = d["value"]["state"]
        self.name = d["value"]["accountName"]
        self.share = d["value"]["shareName"]
        return self


class ServiceState(Service):
    state: str
    docker: str

    def load(self, d: typing.Dict[str, typing.Any]):
        az_cmd = self.path.ctx.az_cmd
        self.name = self.path.key()
        self.state = d["state"]
        self.docker = d["siteConfig"]["linuxFxVersion"]
        self.container = Container.parse(self.docker)
        self.mounts = {
            d["name"]: MountState.build(self, "mounts", d["value"]["mountPath"]).load(d)
            for d in az_cmd.list_webapp_shares(self)
        }
        return self

    def get_docker_spec(self) -> str:
        return f"DOCKER|{self.docker_url()}"

    def docker_url(self):
        repo: RepoState = self.path.absolute(
            "acrs", self.container.acr, "repos", self.container.repo
        ).get_state()
        return f"{repo.url()}:{repo.by_tag[self.container.tag].git}"


class AppServicePlanState(AppServicePlan):
    def load(self, d: typing.Dict[str, typing.Any]) -> "AppServicePlanState":
        self.name = self.path.key()
        self.sku = d["sku"]["name"]
        self.services = {}
        return self


class WebServicesState(WebServicesConfig):
    location_mapping: typing.Dict[str, str]

    def location_id(self, name):
        return self.location_mapping[azwebapps.guess_location_from_display_name(name)]

    def load(self):
        az_cmd = self.path.ctx.az_cmd
        config: WebServicesConfig = self.path.get_config()
        self.group = config.group
        self.location_mapping = az_cmd.get_location_mapping()

        self.acrs = {
            d["name"]: AcrState.build(self, "acrs", d["name"]).load()
            for d in az_cmd.get_acr_list()
        }

        self.storages = {
            d["name"]: StorageState.build(self, "storages", d["name"]).load(d)
            for d in az_cmd.get_storage_list()
        }

        self.plans = {
            d["name"]: AppServicePlanState.build(self, "plans", d["name"]).load(d)
            for d in az_cmd.get_plan_list()
        }

        for d in az_cmd.list_services():
            plan_name = d["appServicePlanId"].split("/")[-1]
            plan = self.plans[plan_name]
            name = d["name"]
            plan.services[name] = ServiceState.build(plan, "services", name).load(d)


class Context:
    config: WebServicesConfig
    state: WebServicesState
    dict_factories: typing.Dict[typing.Type, typing.Callable]
    az_cmd: "AzCmd"

    def root(self):
        return CtxPath(self)


from .cmd import AzCmd
