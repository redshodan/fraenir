import logging
from argparse import ArgumentParser, Action

from .db import User, Room, MessageType, Message


log = logging.getLogger(__name__)


class CommandError(Exception):
    def __init__(self, msg):
        super().__init__()
        self.msg = msg


def registerCmd(cmd):
    CommandParser.registerCmd(cmd)


class BaseParser(ArgumentParser):
    def error(self, message):
        usage = self.format_usage()
        usage += f"{self.prog}: error: {message}"
        raise CommandError(usage)


class CommandParser(BaseParser):
    CMDS = {}

    def __init__(self, name):
        super().__init__(prog="fraenir", add_help=False)
        self.prefixes = [name, f"{name}:", f"@{name}", f"@{name}:"]
        self.subparsers = self.add_subparsers()
        for cmd in CommandParser.CMDS.values():
            self.subparsers._name_parser_map[cmd.NAME] = cmd
            for flag in cmd.FLAGS:
                self.subparsers._name_parser_map[flag] = cmd

    @staticmethod
    def registerCmd(cmd):
        CommandParser.CMDS[cmd.NAME] = cmd()

    def parse(self, line):
        log.info(f"CP parse: {line}")
        if not len([p for p in self.prefixes if line.startswith(p)]):
            return False

        try:
            args = self.parse_args(line.split(" ")[1:])
            print(args)
        except CommandError as e:
            return e.msg

        return True


@registerCmd
class Help(BaseParser):
    NAME = "help"
    FLAGS = ["-h"]
    HELP = "Print this help message"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument("--foo", action="store_true")

    # def __call__(self, parser, namespace, values, option_string=None):
    #     print("HELP ACTION")
