import inspect
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import azwebapps.context as c
from azwebapps.cmd import AzCmd, Player, Recorder, parse_recorder_file


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
        print(f"Replaying: {' '.join(cmd_line)}")
        # args = cmd_line
        az_cmd = AzCmd(replay_from=Player(records))
    else:
        az_cmd = AzCmd()

    show_help = len(args) < 2 or options.get("h", False)
    ctx = c.Context(az_cmd)
    ctx.load_config(args[0])

    if show_help:

        print("\nUSAGES:")
        actions = [f for f in dir(Actions) if not f.startswith("_")]
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
            print(f" {sys.argv[0]} {a} {a_args}")
        print()
