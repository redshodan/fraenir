import os
import sys
import json
import logging
from datetime import datetime

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema

from .commands import CommandParser
from . import db
from .db import FrCryptoStore, User, Room, MessageType, Message


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
            if ("m.relates_to" in event["content"] and
                "m.in_reply_to" in event["content"]["m.relates_to"]):
                reply_to_id = event["content"]["m.relates_to"]["m.in_reply_to"]["event_id"]
            else:
                reply_to_id = None
            line = event["content"]["body"].strip()
            ret = cmds.parse(line)
            if ret is False:
                log.info("Logged")
                Message.log(
                    MessageType.MSG, room, event["event_id"], event["sender"],
                    datetime.fromtimestamp(event["origin_server_ts"] / 1000.0),
                    line, reply_to_id)
            elif isinstance(ret, str):
                room.send_text(ret)
    else:
        print(event['type'])
        print(dir(event))
        print(dir(room))


def run():
    global mxcfg, cmds, client

    logging.basicConfig(level=logging.INFO)

    cfg = json.loads(open("config.json").read())
    mxcfg = cfg["matrix"]
    fcfg = cfg["fraenir"]

    cmds = CommandParser(mxcfg["user"])
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
    token = client.login(mxcfg["user_id"], mxcfg["password"])
    client.add_listener(onMessage)

    try:
        for name in mxcfg["rooms"]:
            room = client.join_room(name)
            room.enable_encryption()
            log.info(f"Connected to room: {room.name} / {room.room_id}")
            #room.add_listener(onMessage)
    except MatrixRequestError as e:
        log.exception(e)
        if e.code == 400:
            log.warn("Room ID/Alias in the wrong format")
            sys.exit(11)
        else:
            log.warn("Couldn't find room.")
            sys.exit(12)

    client.listen_forever()


if __name__ == "__main__":
    run()
