import sys

import azwebapps.context as c
from azwebapps.cmd import AzCmd


class StateContext(c.Context):
    def __init__(self, az_cmd: AzCmd):
        self.az_cmd = az_cmd
        az_cmd.ctx = self


class Actions:
    def purge_acr(self, config_yml):
        pass

    def syncup_apps(self, config_yml):
        pass

    def dump_config(self, resource_group):
        pass


# repo_states = {n: RepoState(repo) for n, repo in config.acr_repos.items()}
# for name, state in repo_states.items():
#     if state.to_remove:
#         print(f'Repo:{name}')
#         for iv in state.to_remove:
#             print(f'purge: {iv}')
#             print(az_cmd.delete_acr_image(config,iv))
# current = {  state.name :state for state in map(ServiceState.from_dict,az_cmd.list_services(config)) }
# desired = {}
# for service in config.services.values():
#     try:
#         docker = repo_states[service.container.repo].get_docker(config, service)
#         desired[service.name] = ServiceState(
#             name = service.name,
#             state = "Running",
#             docker = docker
#             )
#     except:
#         print(f"Cannot create appservice {service.name} with tag:{service.container.tag}")
# if current != desired:
#     all_service_names = set(current.keys())
#     all_service_names.update(desired.keys())
#     for sn in all_service_names:
#         if sn not in current:
#             print(f"create: {desired[sn]}")
#             print(az_cmd.create_webapp(config, desired[sn]))
#         elif sn not in desired:
#             print(f"delete: {current[sn]}")
#             print(az_cmd.delete_webapp(config, current[sn]))
#         elif desired[sn] != current[sn]:
#             print(f"update: {desired[sn]}")
#             print(f"  from: {current[sn]}")
#             print(az_cmd.update_webapp_docker(config, desired[sn]))
#             print(az_cmd.restart_webapp(config, desired[sn]))
#


def main(args=sys.argv[1:], az_cmd=AzCmd):
    ctx = StateContext(az_cmd)
    ctx.dict_factories = c.CONFIG_FACTORIES
    ctx.config = c.load_config(ctx.root(), args[0])
    ctx.state = c.WebServicesState(ctx.root())
    ctx.state.load()
