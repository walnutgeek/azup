import sys
from azwebapps.cmd import AzCmd
from azwebapps.config import load_config
from azwebapps.state import WebServicesState
from azwebapps.context import Context


def main(args=sys.argv[1:], az_cmd=AzCmd):
    ctx = Context()
    ctx.az_cmd = az_cmd
    ctx.config = load_config(ctx.root(), args[0])
    ctx.state = WebServicesState(ctx.root())
    # ctx.state.load()

