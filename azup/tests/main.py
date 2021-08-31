import sys
from datetime import datetime

from azup import CliActions, filter_options, print_err
from azup.cmd import AzCmd, Player, Recorder, add_test, parse_recorder_file
from azup.main import main


class TestActions(CliActions):
    def test_help(self):
        print_err(self._help)

    def list_tests(self):
        pass

    def list_steps(self, test):
        pass

    def print_step(self, test, step="*"):
        pass


def t_main(test_args=sys.argv[1:], now=datetime.utcnow()):
    args, options = filter_options(test_args)

    rec = None
    play = None

    actions = TestActions()
    if "replay" in options:
        cmd_line, records = parse_recorder_file(options["replay"])
        if not len(args):
            print_err(f"Replaying: {' '.join(cmd_line)}")
            args = cmd_line
        play = Player(records)
    else:
        action = args[0]
        if "record" in options:
            rec = Recorder(options["record"], args)
            test_args.remove(f"-record:{options['record']}")
        elif "add_test" in options:
            rec = Recorder(f"{action}*", args)
        elif actions._check_action(action):
            return actions._invoke(args)
        else:
            return main(test_args)

    out = main(args, AzCmd(record_to=rec, replay_from=play, now=now))

    if "add_test" in options:
        test_args.remove("-add_test")
        if play is None:
            print_err(f"Added to cmd line: {rec.replay_option()}")
            test_args.append(rec.replay_option())
        add_test(test_args, out)

    return out


if __name__ == "__main__":
    print(t_main())
