import typing
from datetime import datetime, timedelta

from dateutil.parser import parse as dt_parse

import azup


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
        keys = set(self.get_config().keys())
        keys.update(self.get_state().keys())
        return keys

    def all_presences(self) -> typing.List["CtxPresence"]:
        """
        :return: [(name, path, in_config, in_state),...]
        """
        return list(
            map(
                lambda n: CtxPresence(
                    self.child(n), n in self.get_config(), n in self.get_state()
                ),
                self.all_keys(),
            )
        )

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
        return ">".join(self.parts)


class CtxPresence(typing.NamedTuple):
    path: CtxPath
    in_config: bool
    in_state: bool

    def name(self):
        return self.path.key()

    def get_state(self):
        return self.path.get_state()

    def get_config(self):
        return self.path.get_config()


class ContextAware:
    path: CtxPath

    def __init__(self, path: CtxPath):
        self.path = path

    @classmethod
    def build(cls, parent: "ContextAware", *parts: str) -> typing.Any:
        return cls(parent.path.child(*parts))

    @classmethod
    def from_dict(
        cls, path: CtxPath, d: typing.Dict[str, typing.Any]
    ) -> "ContextAware":
        o = cls(path)
        if not path.is_root():
            o.name = path.key()  # type:ignore
        setattrs_from_dict(o, path, d)
        return o

    def update(self, **props):
        for k, v in props.items():
            setattr(self, k, v)
        return self


# container image repo

PURGE = "purge"
IN_USE = "in_use"


class ImageVer:
    repo_path: CtxPath
    digest: str
    timestamp: datetime
    labels: typing.List[str]
    git: str
    tags: typing.Set[str]

    def __init__(self, repo_path: CtxPath, d: typing.Dict[str, typing.Any]):
        self.repo_path = repo_path
        self.digest = d["digest"]
        self.timestamp = dt_parse(d["timestamp"]).replace(tzinfo=None)
        self.labels = []
        self.tags = set()
        self.git = None
        self.time_to_purge = None
        for t in d["tags"]:
            if len(t) == 40:
                self.git = t
            else:
                self.labels.append(t)

    def all_ids(self):
        return set(t for t in (*self.labels, self.git, self.digest) if t)

    def __str__(self):
        return (
            f"{self.digest} {self.timestamp} {self.git}"
            f" {self.labels} {' '.join(self.tags)}"
        )

    def __repr__(self):
        return str(self)

    def set_tag(self, tag: str, sw: bool):
        if sw:
            self.tags.add(tag)
        elif tag in self.tags:
            self.tags.remove(tag)
        return self


class Repository(ContextAware):
    name: str
    purge_after: timedelta

    def url(self):
        acr: Acr = self.path.parent(2).get_config()
        return f"{acr.name}.azurecr.io/{acr.name}/{self.name}"


class RepositoryState(Repository):
    vers: typing.List[ImageVer]
    by_tag: typing.Dict[str, ImageVer]

    def load(self, acr: "AcrState"):
        az_cmd = self.path.ctx.az_cmd
        self.name = self.path.key()
        self.vers = sorted(
            (ImageVer(self.path, v) for v in az_cmd.show_manifests(self, acr)),
            key=lambda iv: iv.timestamp,
        )
        self.by_tag = {k: iv for iv in self.vers for k in iv.all_ids()}
        return self

    def to_remove(self) -> typing.List[ImageVer]:
        ctx = self.path.ctx
        now = ctx.az_cmd.utcnow()
        repo: Repository = self.path.get_config()
        cutoff = now - repo.purge_after
        for iv in self.vers:
            iv.set_tag(PURGE, iv.timestamp < cutoff)
        for tag in ctx.state.find_all_tags_in_use(self):
            self.by_tag[tag].set_tag(IN_USE, True).set_tag(PURGE, False)
        return [iv for iv in self.vers if PURGE in iv.tags]


class Acr(ContextAware):
    name: str
    repos: typing.Dict[str, Repository]


class AcrState(Acr):
    def load(self) -> "AcrState":
        az_cmd = self.path.ctx.az_cmd
        self.name = self.path.key()
        self.repos = {
            n: RepositoryState.build(self, "repos", n).load(self)
            for n in az_cmd.get_acr_repo_list(self)
        }
        return self


# storage


class FileShare(ContextAware):
    name: str
    quota: int
    key_used: int


class FileShareState(FileShare):
    def load(self, d: typing.Dict[str, typing.Any]):
        self.name = self.path.key()
        self.quota = d["properties"]["quota"]
        return self


class Storage(ContextAware):
    name: str
    shares: typing.Dict[str, FileShare]


class StorageState(Storage):
    access_tier: str
    keys: typing.List[str] = None

    def load(self, d: typing.Dict[str, typing.Any]):
        az_cmd = self.path.ctx.az_cmd
        self.name = self.path.key()
        self.access_tier = d["accessTier"]
        self.shares = {
            d["name"]: FileShareState.build(self, "shares", d["name"]).load(d)
            for d in az_cmd.list_file_shares(self)
        }
        return self

    def get_keys(self) -> typing.List[str]:
        az_cmd = self.path.ctx.az_cmd
        if self.keys is None:
            self.keys = [d["value"] for d in az_cmd.list_storage_keys(self)]
        return self.keys


# app services


class Container:
    acr: str
    repo: str
    tag: str

    @classmethod
    def from_dict(cls, path: CtxPath, d: typing.Dict[str, typing.Any]) -> "Container":
        return setattrs_from_dict(cls(), path, d)

    @classmethod
    def parse(cls, docker_spec: str) -> "Container":
        o = cls()
        _, o.acr, rest = docker_spec.split("|")[1].split("/")
        o.repo, o.tag = rest.split(":")
        return o

    def url(self):
        return f"{self.acr}.azurecr.io/{self.acr}/{self.repo}"


class MongoDb(ContextAware):
    name: str


class MongoDbState(MongoDb):
    connections: typing.List[str] = None

    def get_connections(self):
        if self.connections is None:
            az_cmd = self.path.ctx.az_cmd
            rr = az_cmd.get_mongo_connections(self)
            self.connections = [v["connectionString"] for v in rr["connectionStrings"]]
        return self.connections

    def load(self):
        self.name = self.path.key()
        return self


class Mount(ContextAware):
    name: str
    account: str
    share: str

    def default_custom_id(self):
        return azup.mount_to_id(self.name)

    def access_key(self):
        acc_path = self.path.absolute("storages", self.account)
        fs: FileShare = acc_path.child("shares", self.share).get_config()
        storage: StorageState = acc_path.get_state()
        return storage.get_keys()[fs.key_used]


class MountState(Mount):
    state: str
    custom_id: str

    def load(self, d: typing.Dict[str, typing.Any]) -> "MountState":
        self.name = self.path.key()
        val = d["value"]
        self.custom_id = d["name"]
        self.state = val["state"]
        self.account = val["accountName"]
        self.share = val["shareName"]
        return self


class MongoConnection(ContextAware):
    name: str
    db: str
    conn_used: int

    def access_key(self):
        mdd: MongoDbState = self.path.absolute("mongos", self.db).get_state()
        return mdd.get_connections()[self.conn_used]


class MongoConnectionState(MongoConnection):
    def load(self, d: typing.Tuple[str, int]) -> "MongoConnectionState":
        self.name = self.path.key()
        self.db, self.conn_used = d
        return self


class Service(ContextAware):
    name: str
    container: Container
    mounts: typing.Dict[str, Mount] = {}
    mongo_connections: typing.Dict[str, MongoConnection] = {}

    def get_docker_spec(self) -> str:
        return f"DOCKER|{self.docker_url()}"

    def resolved_tag(self):
        repo: RepositoryState = self.path.absolute(
            "acrs", self.container.acr, "repos", self.container.repo
        ).get_state()
        return repo.by_tag[self.container.tag].git

    def docker_url(self):
        return f"{self.container.url()}:{self.resolved_tag()}"

    def create(self):
        az_cmd = self.path.ctx.az_cmd
        az_cmd.create_webapp(self)
        for mount in self.mounts.values():
            az_cmd.mount_share(mount)
        for conn in self.mongo_connections.values():
            az_cmd.set_app_settings(self, conn.name, conn.access_key())


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
            d["value"]["mountPath"]: MountState.build(
                self, "mounts", d["value"]["mountPath"]
            ).load(d)
            for d in az_cmd.list_webapp_shares(self)
        }
        mongoStates: typing.Iterable[MongoDbState] = (
            self.path.absolute("mongos").get_state().values()
        )
        db_by_cs: typing.Dict[str, typing.Tuple[str, int]] = {
            conn_string: (db.name, i)
            for db in mongoStates
            for i, conn_string in enumerate(db.get_connections())
        }
        self.mongo_connections = {
            d["name"]: MongoConnectionState.build(
                self, "mongo_connections", d["name"]
            ).load(db_by_cs[d["value"]])
            for d in az_cmd.get_app_settings(self)
            if d["value"] in db_by_cs
        }
        return self

    def update(self):
        service: Service = self.path.get_config()
        service.container.tag = service.resolved_tag()
        if to_yaml(service, YAMLABLE_OBJECTS) != to_yaml(self, YAMLABLE_OBJECTS):
            self.delete()
            service.create()

    def delete(self):
        az_cmd = self.path.ctx.az_cmd
        az_cmd.delete_webapp(self)


class AppServicePlan(ContextAware):
    name: str
    sku: str
    kind: str
    location: str
    services: typing.Dict[str, Service]

    def create(self):
        az_cmd = self.path.ctx.az_cmd
        az_cmd.create_app_plan(self)


class AppServicePlanState(AppServicePlan):
    def load(self, d: typing.Dict[str, typing.Any]) -> "AppServicePlanState":
        state: WebServicesState = self.path.ctx.state
        self.name = self.path.key()
        self.sku = d["sku"]["name"]
        self.kind = d["kind"]
        self.location = state.location_id(d["location"])
        self.services = {}
        return self

    def can_update(self):
        plan: AppServicePlan = self.path.get_config()
        plan.location = self.path.ctx.state.location_id(plan.location)
        return all(getattr(self, n) == getattr(plan, n) for n in ("kind", "location"))

    def update(self):
        assert self.can_update()
        plan: AppServicePlan = self.path.get_config()
        if self.sku != plan.sku:
            self.path.ctx.az_cmd.update_app_plan_sku(plan)

    def delete(self):
        az_cmd = self.path.ctx.az_cmd
        az_cmd.delete_app_plan(self)


# root objects


class WebServicesConfig(ContextAware):
    group: str
    storages: typing.Dict[str, Storage]
    plans: typing.Dict[str, AppServicePlan]
    acrs: typing.Dict[str, Acr]
    mongos: typing.Dict[str, MongoDb]


class WebServicesState(WebServicesConfig):
    location_mapping: typing.Dict[str, str]

    def location_id(self, name):
        return self.location_mapping[azup.cleanup_misc_chars(name)]

    def load(self):
        az_cmd = self.path.ctx.az_cmd
        config: WebServicesConfig = self.path.get_config()
        self.group = config.group
        self.location_mapping = az_cmd.get_location_mapping()

        self.acrs = {
            d["name"]: AcrState.build(self, "acrs", d["name"]).load()
            for d in az_cmd.get_acr_list()
        }
        self.mongos = {
            d["name"]: MongoDbState.build(self, "mongos", d["name"]).load()
            for d in az_cmd.list_cosmos_dbs()
        }

        self.storages = {
            d["name"]: StorageState.build(self, "storages", d["name"]).load(d)
            for d in az_cmd.get_storage_list()
        }
        self.load_service_plans()
        return self

    def load_service_plans(self):
        az_cmd = self.path.ctx.az_cmd
        self.plans = {
            d["name"]: AppServicePlanState.build(self, "plans", d["name"]).load(d)
            for d in az_cmd.get_plan_list()
        }
        for d in az_cmd.list_services():
            plan_name = d["appServicePlanId"].split("/")[-1]
            plan = self.plans[plan_name]
            name = d["name"]
            plan.services[name] = ServiceState.build(plan, "services", name).load(d)

    def find_all_tags_in_use(self, repo: RepositoryState) -> typing.List[str]:
        acr: AcrState = repo.path.parent(2).get_state()
        return [
            service.container.tag
            for plan in self.plans.values()
            for service in plan.services.values()
            if service.container.repo == repo.name and service.container.acr == acr.name
        ]


YAMLABLE_OBJECTS = (
    WebServicesConfig,
    AppServicePlan,
    MongoDb,
    Service,
    Container,
    Mount,
    MongoConnection,
    Storage,
    FileShare,
    Acr,
    Repository,
)


class Context:
    config: WebServicesConfig
    state: WebServicesState
    az_cmd: "AzCmd"

    str_factories: typing.Dict[typing.Type, typing.Callable] = {}
    dict_factories: typing.Dict[typing.Type, typing.Callable] = {}

    def __init__(self, az_cmd: "AzCmd"):
        self.az_cmd = az_cmd
        az_cmd.ctx = self

    def root(self):
        return CtxPath(self)

    def load_config(self, config_file):
        self.init_context(
            lambda root: load_from_file(config_file, root, WebServicesConfig)
        )

    def init_context(
        self, config_factory: typing.Callable[[CtxPath], WebServicesConfig]
    ):
        root = self.root()
        root.ctx.dict_factories = build_factory_dict(YAMLABLE_OBJECTS)
        root.ctx.str_factories = azup.FROM_STR_FACTORIES
        self.config = config_factory(root)
        self.state = WebServicesState(root)
        self.state.load()


from azup.cmd import AzCmd
from azup.yaml import (
    build_factory_dict,
    load_from_file,
    setattrs_from_dict,
    to_yaml,
)
