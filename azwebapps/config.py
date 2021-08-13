import yaml
from yaml.loader import SafeLoader
from typing import Dict, Any, List
from datetime import timedelta
from azwebapps.context import ContextAware, CtxPath, setattrs_from_dict


class FileShare(ContextAware):
    name: str
    quota: int
    key_used: int

    @classmethod
    def from_dict(cls, path:CtxPath, d: Dict[str, Any]):
        o = cls(path)
        o.name = path.key()
        setattrs_from_dict(o, path, d, from_dict_factories=CONFIG_FACTORIES)
        return o

class Storage(ContextAware):
    account: str
    shares: Dict[str, FileShare]

    @classmethod
    def from_dict(cls, path:CtxPath, d: Dict[str, Any]):
        o = cls(path)
        o.account = path.key()
        setattrs_from_dict(o, path, d, from_dict_factories=CONFIG_FACTORIES)
        return o

class Container:
    acr: str
    repo: str
    tag: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return setattrs_from_dict(cls(), None, d, from_dict_factories=CONFIG_FACTORIES)

class Mount(ContextAware):
    mount_dir: str
    account: str
    share: str

    @classmethod
    def from_dict(cls, path:CtxPath, d: Dict[str, Any]):
        o = cls(path)
        o.mount_dir = path.key()
        setattrs_from_dict(o, path, d, from_dict_factories=CONFIG_FACTORIES)
        return o

class Service(ContextAware):
    name: str
    container: Container
    shares: Dict[str, Mount]

    @classmethod
    def from_dict(cls, path:CtxPath, d: Dict[str, Any]):
        o = cls(path)
        o.name = path.key()
        setattrs_from_dict(o, path, d, from_dict_factories=CONFIG_FACTORIES)
        return o

class AppServicePlan(ContextAware):
    name: str
    sku: str
    services: Dict[str, Service]

    @classmethod
    def from_dict(cls, path:CtxPath, d: Dict[str, Any]):
        o = cls(path)
        o.name = path.key()
        setattrs_from_dict(o, path, d, from_dict_factories=CONFIG_FACTORIES)
        return o





class Repository(ContextAware):
    name: str
    user: str
    purge_after: timedelta

    def url(self):
        return f"{self.user}.azurecr.io/{self.user}/{self.name}"

    @classmethod
    def from_dict(cls, path:CtxPath, d: Dict[str, Any]):
        o = cls(path)
        o.name = path.key()
        setattrs_from_dict(o, path, d, from_dict_factories=CONFIG_FACTORIES)
        return o

class Acr(ContextAware):
    name: str
    repos: Dict[str, Repository]

    @classmethod
    def from_dict(cls, path:CtxPath, d: Dict[str, Any]):
        o = cls(path)
        o.name = path.key()
        setattrs_from_dict(o, path, d, from_dict_factories=CONFIG_FACTORIES)
        return o


class WebServicesConfig(ContextAware):
    group: str
    plan: str
    storages: Dict[str, Storage]
    plans: Dict[str, AppServicePlan]
    acrs: Dict[str, Acr]

    @classmethod
    def from_dict(cls, path:CtxPath, d: Dict[str, Any]):
        return setattrs_from_dict(cls(path), path, d, from_dict_factories=CONFIG_FACTORIES)

CONFIG_FACTORIES = { cls : cls.from_dict for cls in ( # type:ignore
    WebServicesConfig, Repository, Service, 
    Container, Storage, Acr, FileShare, Mount
)}

def load_config(root:CtxPath, f):
    with open(f) as fp:
        return WebServicesConfig.from_dict(root, yaml.load(fp, Loader=SafeLoader))
