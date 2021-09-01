import sys
from typing import List

import azup.context as c
from azup import CliActions, filter_options, print_err
from azup.cmd import AzCmd
from azup.yaml import to_yaml


class Actions(CliActions):
    def __init__(self, az_cmd: AzCmd):
        super(Actions, self).__init__()
        self.ctx = c.Context(az_cmd)

    def list_images(self, config_yml):
        self.ctx.load_config(config_yml)
        out = []
        for acr_name, acr in self.ctx.state.acrs.items():
            for repo_name in acr.repos:
                repo: c.RepositoryState = acr.repos[repo_name]
                repo.to_remove()
                out.append(f"Repo: {acr_name}/{repo_name}")
                for iv in repo.vers:
                    out.append(str(iv))
        return "\n".join(out) + "\n"

    def purge_acr(self, config_yml):
        self.ctx.load_config(config_yml)
        for acr_name, acr in self.ctx.state.acrs.items():
            for repo_name in acr.repos:
                repo: c.RepositoryState = acr.repos[repo_name]
                to_remove = repo.to_remove()
                if len(to_remove):
                    print_err(f"Repo: {acr_name}/{repo_name}")
                    for iv in to_remove:
                        print_err(f"purge: {iv}")
                        print_err(self.ctx.az_cmd.delete_acr_image(iv))

    def syncup_apps(self, config_yml):
        self.ctx.load_config(config_yml)
        plans_path = self.ctx.root().child("plans")
        # Delete services and plans that not mentioned in config, and create plans
        # that does not exist in azure
        need_reload = False
        for plan in plans_path.all_presences():

            if not plan.in_state:
                plan.get_config().create()
                need_reload = True
                continue
            elif plan.in_config:
                if plan.get_state().can_update():
                    for service in plan.path.child("services").all_presences():
                        if not service.in_config:
                            service.get_state().delete()
                            need_reload = True
                    continue

            need_reload = True
            for service in plan.get_state().services.values():
                service.delete()
            plan.get_state().delete()
            if plan.in_config:
                plan.get_config().create()

        # Reload all plans
        if need_reload:
            self.ctx.state.load_service_plans()

        # All plans should be present in both config and state,
        # just to ensure that they are updated, and then create or update all
        # it's services
        for plan in plans_path.all_presences():
            assert plan.in_state and plan.in_config, f"{plan} should be created already"
            plan.get_state().update()
            for service in plan.path.child("services").all_presences():
                assert service.in_config, f"{service} should be mentioned in config"
                if not service.in_state:
                    service.get_config().create()
                else:
                    service.get_state().update()

    def dump_config(self, resource_group):
        self.ctx.init_context(
            lambda root: c.WebServicesState(root).update(group=resource_group)
        )
        return to_yaml(self.ctx.state, c.YAMLABLE_OBJECTS)


def main(args: List[str] = sys.argv[1:], az_cmd: AzCmd = None):
    args, options = filter_options(args)
    if az_cmd is None:
        az_cmd = AzCmd()
    actions = Actions(az_cmd)
    actions._show_help = len(args) == 0 or "h" in options
    out = actions._invoke(*args)
    if actions._show_help:
        print_err(actions._help)
    return out


def print_main():
    print(main() or "")


if __name__ == "__main__":
    print_main()
