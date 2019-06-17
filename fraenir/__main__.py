import os
import sys
import json
import logging

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError

from .commands import CommandParser
from . import db
from .db import FrCryptoStore


log = logging.getLogger(__name__)
cmds = None
client = None
mxcfg = None


# Called when a message is recieved.
def onMessage(*args):
    if len(args) == 1:
        event = args[0]
        room = client.rooms[event['room_id']]
    elif len(args) == 2:
        room, event = args
    log.info(f"onMessage: {repr(room)} {json.dumps(event)}")
    if room.room_id not in mxcfg["rooms"]:
        log.info(f"Skipping event for unknown room: {room.room_id}")
        return
    if event["sender"] == mxcfg["user_id"]:
        log.info(f"Skipping my own event")
        return

    if event['type'] == "m.room.member":
        if 'membership' in event and event['membership'] == "join":
            log.info(f"{event['content']['displayname']} joined")
    elif event['type'] == "m.room.message":
        if event['content']['msgtype'] == "m.text":
            log.info(f"{event['sender']}: {event['content']['body']}")
            ret = cmds.parse(room, event)
            if ret:
                room.send_text(ret)
    else:
        log.info(f"Unhandled event of type: {event['type']}")


def run():
    global mxcfg, cmds, client

    logging.basicConfig(level=logging.INFO)

    cfg = json.loads(open("config.json").read())
    mxcfg = cfg["matrix"]
    fcfg = cfg["fraenir"]

    cmds = CommandParser(mxcfg["user"], fcfg["cmd-prefix"])
    db.init(fcfg)

    mxcfg["user_id"] = f"@{mxcfg['user']}:{mxcfg['domain']}"
    kwargs = {"user_id": mxcfg['user'],
              "encryption": True if mxcfg["encryption"] else False}
    if mxcfg["encryption"]:
        kwargs["restore_device_id"] = True
        kwargs["encryption_conf"] = \
            {'store_conf':
             {'db_path': os.path.abspath(os.path.dirname(fcfg["db"])),
              'db_name': os.path.basename(fcfg["db"])},
             'Store': FrCryptoStore}
    client = MatrixClient(mxcfg["homeserver"], **kwargs)
    client.login(mxcfg["user_id"], mxcfg["password"])
    client.add_listener(onMessage)

    try:
        for name in mxcfg["rooms"]:
            room = client.join_room(name)
            room.enable_encryption()
            log.info(f"Connected to room: {room.name} / {room.room_id}")
            # room.add_listener(onMessage)
    except MatrixRequestError as e:
        log.exception(e)
        if e.code == 400:
            log.warn("Room ID/Alias in the wrong format")
            sys.exit(11)
        else:
            log.warn("Couldn't find room.")
            sys.exit(12)

    try:
        client.listen_forever()
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt. Shutting down.")


if __name__ == "__main__":
    run()
