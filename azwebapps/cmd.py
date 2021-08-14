import json
import subprocess
import sys
from typing import Dict

from azwebapps import guess_location_from_display_name


class CmdRun:
    cmd: str
    out: str
    err: str
    rc: int

    def __init__(self, cmd, rc=None, out=None, err=None):
        self.cmd = cmd
        if rc is None:
            print(f"run: {cmd}")
            process = subprocess.run(cmd.split(), capture_output=True)
            self.rc = process.returncode
            self.out = process.stdout.decode("utf-8")
            self.err = process.stderr.decode("utf-8")
        else:
            self.err = err or ""
            self.out = out or ""
            self.rc = rc


class Cmd:
    run: CmdRun
    ctx: "c.Context"

    def __init__(self, cmd: str, show_err: bool = True):
        self.run = CmdRun(cmd)
        if show_err and self.run.err:
            print(self.run.err, file=sys.stderr)
        if self.run.rc != 0:
            raise ValueError(f"rc:{self.run.rc}")

    def json(self):
        try:
            return json.loads(self.run.out)
        except:
            print(f"not json: {self.run.out}", file=sys.stderr)
            return None

    def text(self):
        return self.run.out


class AzCmd(Cmd):
    @classmethod
    def get_location_mapping(cls) -> Dict[str, str]:
        all_locations = cls(f"az account list-locations").json()
        mapping = {}
        for l in all_locations:
            name = l["name"]
            mapping[guess_location_from_display_name(l["displayName"])] = name
            mapping[name] = name
        return mapping

    @classmethod
    def get_acr_list(cls):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(f"az acr list -g {config.group}").json()

    @classmethod
    def get_plan_list(cls):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(f"az appservice plan list -g {config.group}").json()

    @classmethod
    def get_storage_list(cls):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(f"az storage account list -g {config.group}").json()

    @classmethod
    def get_acr_repo_list(cls, acr: "c.Acr"):
        return [
            path.split("/")[1]
            for path in cls(f"az acr repository list -n {acr.name}").json()
        ]

    @classmethod
    def show_manifests(cls, repo: "c.Repository", acr: "c.Acr" = None):
        if acr is None:
            acr = repo.path.parent(2).get_state()
        return cls(
            f"az acr repository show-manifests -n {acr.name} --repository {acr.name}/{repo.name}"
        ).json()

    @classmethod
    def list_storage_keys(cls, storage: "c.Storage"):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(
            f"az storage account keys list -g {config.group} -n {storage.name}"
        ).json()

    @classmethod
    def list_file_shares(cls, storage: "c.Storage"):
        return cls(
            f"az storage share list --account-name {storage.name} ", show_err=False
        ).json()

    @classmethod
    def list_services(cls):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(f"az webapp list --resource-group {config.group}").json()

    @classmethod
    def get_service_props(cls, ss: "c.ServiceState"):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(
            f"az webapp config container show -n {ss.name} -g {config.group}"
        ).json()

    @classmethod
    def list_service_props(cls, ss: "c.ServiceState"):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(
            f"az webapp config container show -n {ss.name} -g {config.group}"
        ).json()

    @classmethod
    def list_webapp_shares(cls, service: "c.Service"):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(
            f"az webapp config storage-account list --resource-group {config.group} --name {service.name}",
            show_err=False,
        ).json()

    @classmethod
    def mount_share(cls, mount: "c.Mount"):
        config: "c.WebServicesConfig" = cls.ctx.config
        service: c.Service = mount.path.parent(2).get_config()
        return cls(
            f"az webapp config storage-account add --resource-group {config.group} --name {service.name} --custom-id {mount.default_custom_id()} --storage-type AzureFiles --share-name {mount.share} --account-name {mount.account} --access-key {mount.access_key()} --mount-path {mount.name}"
        ).json()

    # az webapp config storage-account list --resource-group {config.group} --name {ss.name}
    # az webapp config storage-account delete --custom-id {sharec.custom_id} --resource-group {config.group} --name {ss.name}

    @classmethod
    def create_webapp(cls, ss: "c.ServiceState"):
        config: "c.WebServicesConfig" = cls.ctx.config
        plan: c.AppServicePlan = ss.path.parent(2).get_config()
        return cls(
            f"az webapp create -n {ss.name} -g {config.group} -p {plan.name} -i {ss.docker_url()}"
        ).json()

    @classmethod
    def delete_acr_image(cls, iv: "c.ImageVer"):
        repo: c.Repository = iv.repo_path.get_config()
        acr: c.Acr = iv.repo_path.parent(2).get_config()
        return cls(
            f"az acr repository delete --yes -n {acr.name} --image {acr.name}/{repo.name}@{iv.digest}"
        ).text()

    @classmethod
    def delete_webapp(cls, ss: "c.Service"):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(f"az webapp delete -n {ss.name} -g {config.group} ").text()

    @classmethod
    def update_webapp_docker(cls, ss: "c.ServiceState"):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(
            f"az webapp config container set -n {ss.name} -g {config.group} -c {ss.docker}"
        ).json()

    @classmethod
    def restart_webapp(cls, ss: "c.ServiceState"):
        config: "c.WebServicesConfig" = cls.ctx.config
        return cls(f"az webapp restart -n {ss.name} -g {config.group}").text()


import azwebapps.context as c
