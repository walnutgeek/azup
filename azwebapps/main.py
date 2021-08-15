import inspect
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import azwebapps.context as c
from azwebapps import print_err
from azwebapps.cmd import AzCmd, Player, Recorder, parse_recorder_file
from azwebapps.yaml import to_yaml


class Actions:
    def __init__(self, az_cmd: AzCmd):
        self.ctx = c.Context(az_cmd)

    def purge_acr(self, config_yml):
        self.ctx.load_config(config_yml)
        for acr_name, acr in self.ctx.state.acrs.items():
            for repo_name in acr.repos:
                repo:c.RepositoryState = acr.repos[repo_name]
                to_remove = repo.to_remove()
                if len(to_remove):
                    print_err(f'Repo: {acr_name}/{repo_name}')
                    for iv in to_remove:
                        print_err(f'purge: {iv}')
                        print_err(self.ctx.az_cmd.delete_acr_image(iv))

    def syncup_apps(self, config_yml):
        self.ctx.load_config(config_yml)

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
    #         print_err(f"Cannot create appservice {service.name} with tag:{service.container.tag}")
    # if current != desired:
    #     all_service_names = set(current.keys())
    #     all_service_names.update(desired.keys())
    #     for sn in all_service_names:
    #         if sn not in current:
    #             print_err(f"create: {desired[sn]}")
    #             print_err(az_cmd.create_webapp(config, desired[sn]))
    #         elif sn not in desired:
    #             print_err(f"delete: {current[sn]}")
    #             print_err(az_cmd.delete_webapp(config, current[sn]))
    #         elif desired[sn] != current[sn]:
    #             print_err(f"update: {desired[sn]}")
    #             print_err(f"  from: {current[sn]}")
    #             print_err(az_cmd.update_webapp_docker(config, desired[sn]))
    #             print_err(az_cmd.restart_webapp(config, desired[sn]))


    def dump_config(self, resource_group):
        self.ctx.init_context(
            lambda root: c.WebServicesState(root).update(group=resource_group)
        )
        return to_yaml(self.ctx.state, c.YAMLABLE_OBJECTS)





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


def main(args: List[str] = sys.argv[1:]):
    args, options = filter_options(args)
    rec_dir = Path("recordings")
    if "record" in options:
        if not rec_dir.is_dir():
            rec_dir.mkdir(0o0755)
        az_cmd = AzCmd(record_to=Recorder(rec_dir / options["record"], args))
    elif "replay" in options:
        cmd_line, records = parse_recorder_file(rec_dir / options["replay"])
        if not len(args):
            print_err(f"Replaying: {' '.join(cmd_line)}")
            args = cmd_line
        az_cmd = AzCmd(replay_from=Player(records))
    else:
        az_cmd = AzCmd()

    actions = [f for f in dir(Actions) if not f.startswith("_")]

    out = ""
    show_help = len(args) == 0 or options.get("h", False)

    if not show_help:
        act = args[0]
        if act not in actions:
            print_err(f"{act} is not valid action")
            show_help = True
        else:
            out = getattr(Actions(az_cmd), act)(*args[1:])

    if show_help:
        print_err("\nUSAGES:")
        for a in actions:
            fn = getattr(Actions, a)
            names, _, _, defaults = inspect.getfullargspec(fn)[:4]
            if defaults is None:
                defaults = ()
            def_offset = len(names) - len(defaults)
            optonals = {k: v for k, v in zip(names[def_offset:], defaults)}
            a_args = " ".join(
                f"[{n}]" if n in optonals else f"<{n}>" for n in names[1:]
            )
            print_err(f" {sys.argv[0]} {a} {a_args}")
        print_err()
    return out

if __name__ == "__main__":
    print(main() or "")
