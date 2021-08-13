import sys
import subprocess
import json
import azwebapps.config as cfg
import azwebapps.state as state


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


class AzCmd:
    run: CmdRun

    @classmethod
    def show_manifests(cls, repo: cfg.Repository):
        return cls(
            f"az acr repository show-manifests -n {repo.user} --repository {repo.user}/{repo.name}"
        ).json()

    @classmethod
    def get_service_props(cls, config:cfg.WebServicesConfig, ss:state.ServiceState):
        return cls(f"az webapp config container show -n {ss.name} -g {config.group}").json()

    @classmethod
    def list_service_props(cls, config:cfg.WebServicesConfig, ss:state.ServiceState):
        return cls(f"az webapp config container show -n {ss.name} -g {config.group}").json()

    @classmethod
    def list_services(cls, config:cfg.WebServicesConfig):
        return cls(f"az webapp list --resource-group {config.group}").json()
    
    @classmethod
    def list_storage_accounts(cls, config:cfg.WebServicesConfig):
        return cls(f"az storage account list -g {config.group}").json()
    
    @classmethod
    def list_storage_keys(cls, config:cfg.WebServicesConfig, storage:cfg.Storage):
        return cls(f"az storage account keys list -g {config.group} -n {storage.account}").json()

    @classmethod
    def list_file_shares(cls, storage:cfg.Storage):
        return cls(f"az storage share list --account-name {storage.account} ", show_err=False).json()

# @classmethod
# def mount_share(cls, config:cfg.WebServicesConfig, storage:cfg.Storage, share:cfg.FileShare):
#     return cls(f"az webapp config storage-account add --resource-group {config.group} --name {share.name} --custom-id {sharestate.custom_id} --storage-type AzureFiles --share-name {share.name} --account-name {storage.account} --access-key {share.access_key()} --mount-path {share.mount_path()}").json()


# az webapp config storage-account list --resource-group {config.group} --name {ss.name}
# az webapp config storage-account delete --custom-id {sharestate.custom_id} --resource-group {config.group} --name {ss.name}

    @classmethod
    def create_webapp(cls, config:cfg.WebServicesConfig, ss: state.ServiceState):
        return cls(
            f"az webapp create -n {ss.name} -g {config.group} -p {config.plan} -i {ss.docker_url()}"
        ).json()

    @classmethod
    def delete_acr_image(cls, config:cfg.WebServicesConfig, iv:state.ImageVer ):
        user = config.acrs[iv.repo_name].name
        return cls(
            f"az acr repository delete --yes -n {user} --image {user}/{iv.repo_name}@{iv.digest}"
        ).text()

    @classmethod
    def delete_webapp(cls, config:cfg.WebServicesConfig, ss: state.ServiceState):
        return cls(
            f"az webapp delete -n {ss.name} -g {config.group} "
        ).text()

    @classmethod
    def update_webapp_docker(cls, config:cfg.WebServicesConfig, ss: state.ServiceState):
        return cls(
            f"az webapp config container set -n {ss.name} -g {config.group} -c {ss.docker}"
        ).json()

    @classmethod
    def restart_webapp(cls, config:cfg.WebServicesConfig, ss: state.ServiceState):
        return cls(
            f"az webapp restart -n {ss.name} -g {config.group}"
        ).text()

    def __init__(self, cmd:str, show_err:bool = True):
        self.run = CmdRun(cmd)
        if show_err and self.run.err:
            print(self.run.err, file=sys.stderr)
        if self.run.rc != 0 :
            raise ValueError(f"rc:{self.run.rc}")

    def json(self):
        try:
            return json.loads(self.run.out)
        except:
            print(f'not json: {self.run.out}', file=sys.stderr)
            return None

    def text(self):
        return self.run.out

