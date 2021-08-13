import typing
from datetime import datetime
from dateutil.parser import parse as dt_parse
import azwebapps.config as cfg
import azwebapps.context as context

class ServiceState(cfg.Service):
    state:str
    docker:str

    @classmethod
    def from_dict(cls, d):
        return cls( 
            name=d["name"],
            state=d["state"],
            docker=d["siteConfig"]["linuxFxVersion"]
            )
    
    def docker_url(self):
        return self.docker.split('|')[1]

class ImageVer:
    def __init__(self, repo_name, json):
        self.repo_name = repo_name
        self.digest = json['digest']
        self.timestamp = dt_parse(json['timestamp']).replace(tzinfo=None)
        self.tags = []
        self.git = None
        for t in json['tags']:
            if len(t) == 40:
                self.git = t
            else:
                self.tags.append(t)

    def __str__(self):
        return f"{self.digest} {self.timestamp} {self.git} {self.tags}"

    def __repr__(self):
        return str(self)

class RepoState(cfg.Repository):
    def __init__(self, repo:cfg.Repository, now:datetime=None):
        if not now:
            now = datetime.utcnow()
        cutoff = now - repo.purge_after
        manifests:typing.List[typing.Any] = [] #TODO az_cmd.show_manifests(repo)
        self.name = repo.name
        self.vers = [ImageVer(repo.name, v) for v in manifests]
        self.to_remove = []
        self.by_tag = {}
        for iv in self.vers:
            if iv.tags:
                for tag in iv.tags:
                    self.by_tag[tag] = iv
            elif iv.timestamp < cutoff:
                self.to_remove.append(iv)
    
    def get_docker(self, config:cfg.WebServicesConfig, service:cfg.Service)->str:
        return f'DOCKER|{config.acrs[self.name].repos[self.name].url()}:{self.by_tag[service.container.tag].git}'

class StorageState(cfg.Storage):
    pass 
class AppServicePlanState(cfg.AppServicePlan):
    pass 

class AcrState(cfg.Acr):
    pass

class WebServicesState(cfg.WebServicesConfig):
    
    def load(az_cmd):
        repo_states = {n: RepoState(repo) for n, repo in config.acr_repos.items()}
        for name, state in repo_states.items():
            if state.to_remove:
                print(f'Repo:{name}')
                for iv in state.to_remove:
                    print(f'purge: {iv}')
                    print(az_cmd.delete_acr_image(config,iv))
        current = {  state.name :state for state in map(ServiceState.from_dict,az_cmd.list_services(config)) }
        desired = {}
        for service in config.services.values():
            try:
                docker = repo_states[service.container.repo].get_docker(config, service)
                desired[service.name] = ServiceState(
                    name = service.name,
                    state = "Running",
                    docker = docker
                    )
            except:
                print(f"Cannot create appservice {service.name} with tag:{service.container.tag}")
        if current != desired:
            all_service_names = set(current.keys())
            all_service_names.update(desired.keys())
            for sn in all_service_names:
                if sn not in current:
                    print(f"create: {desired[sn]}")
                    print(az_cmd.create_webapp(config, desired[sn]))
                elif sn not in desired:
                    print(f"delete: {current[sn]}")
                    print(az_cmd.delete_webapp(config, current[sn]))
                elif desired[sn] != current[sn]:
                    print(f"update: {desired[sn]}")
                    print(f"  from: {current[sn]}")
                    print(az_cmd.update_webapp_docker(config, desired[sn]))
                    print(az_cmd.restart_webapp(config, desired[sn]))

    