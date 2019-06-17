import logging
from argparse import ArgumentParser
from datetime import datetime

from ..db import Message


log = logging.getLogger(__name__)


class CommandError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message


class HelpError(Exception):
    pass


def registerCmd(cmd):
    CommandParser.CMDS[cmd.NAME] = cmd()


class SafeArgParser(ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.exit_message = None
        self.safe_parent = None
        super().__init__(*args, **kwargs)

    def print_usage(self, file=None):
        self.exitMessage(self.format_usage())

    def print_help(self, file=None):
        self.exitMessage(self.format_help())

    def _print_message(self, message, file=None):
        self.exitMessage(message)

    def parse_args(self, args=None, namespace=None):
        self.exit_message = None
        return super().parse_args(args, namespace)

    def exit(self, status=0, message=None):
        self.exitMessage(message)
        raise HelpError()

    def exitMessage(self, message):
        if not message:
            return
        if self.safe_parent:
            parser = self.safe_parent
        else:
            parser = self
        if parser.exit_message is None:
            parser.exit_message = message
        else:
            parser.exit_message = parser.exit_message + "\n" + message


class CommandParser:
    CMDS = {}

    def __init__(self, name, cmd_prefix):
        self.parser = SafeArgParser(prog=name, add_help=False)
        self.prefixes = [name, f"{name}:", f"@{name}", f"@{name}:"]
        self.cmd_prefix = cmd_prefix

        self.parser.add_argument("-h", "--help", action="help")
        self.parser.set_defaults(func=self)
        self.subparsers = self.parser.add_subparsers()
        for cmd in CommandParser.CMDS.values():
            parser = self.subparsers.add_parser(cmd.NAME, **cmd.KWARGS)
            parser.set_defaults(func=cmd)
            parser.safe_parent = self.parser

    def parse(self, room, event):
        line = event["content"]["body"].strip()
        log.info(f"CP parse: {line}")
        words = None
        if len([p for p in self.prefixes if line.startswith(p)]):
            words = line.split(" ")[1:]
            line = " ".join(words)
        if line.startswith(self.cmd_prefix):
            words = line[1:].split(" ")
        if not words:
            return self.log(room, event)

        try:
            args = self.parser.parse_args(words)
            if self.parser.exit_message:
                return self.parser.exit_message
            else:
                return args.func(args)
        except HelpError:
            if self.parser.exit_message:
                return self.parser.exit_message
            else:
                return self.parser.format_help()
        except CommandError as e:
            return e.message

        return True

    def log(self, room, event):
        log.info("Logging...")
        if ("m.relates_to" in event["content"] and
              "m.in_reply_to" in event["content"]["m.relates_to"]):
            reply_to_id = (event["content"]["m.relates_to"]
                           ["m.in_reply_to"]["event_id"])
        else:
            reply_to_id = None
        line = event["content"]["body"].strip()
        Message.log("message", room, event["event_id"], event["sender"],
                    datetime.fromtimestamp(event["origin_server_ts"] / 1000.0),
                    line, reply_to_id)

    def __call__(self, args):
        return self.parser.format_help()


from . import search, fermi
