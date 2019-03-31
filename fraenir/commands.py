import logging
from argparse import ArgumentParser

from .db import User, Room, MessageType, Message


log = logging.getLogger(__name__)


def registerCmd(cmd):
    CommandParser.registerCmd(cmd)


class Command():
    NAME = None
    HELP = None

    def __init__(self):
        pass

    def run(self, cmd, args):
        pass


class CommandParser(ArgumentParser):
    cmds = {}

    def __init__(self, name):
        super().__init__(prog="fraenir")
        self.name = name
        self.prefixes = [f"{name}:", f"@{name}", f"@{name}:"]
        self.subparsers = self.add_subparsers()

    @staticmethod
    def registerCmd(cmd):
        CommandParser.cmds[cmd.NAME] = cmd

    def parse(self, line):
        log.info(f"CP parse: {line}")
        if not len([p for p in self.prefixes if line.startswith(p)]):
            return False

        args = self.parse_args(line.split(" ")[1:])
        print(args)

        return True


@CommandParser.registerCmd
class Help(Command):
    NAME = "help"
    HELP = "Show this help message"

    def run(self, cmd, args):
        print(f"Help: {cmd} : {args}")
