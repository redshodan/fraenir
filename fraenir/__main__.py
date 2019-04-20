import sys
import json
import logging

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema

from .commands import CommandParser
from . import db
from .db import FrCryptoStore, User, Room, MessageType, Message


log = logging.getLogger(__name__)
cmds = None


# Called when a message is recieved.
def onMessage(room, event):
    log.info(f"onMessage: {repr(room)} {json.dumps(event)}")
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
                Message.log(MessageType.MSG, room, event["event_id"],
                            event["sender"], line, reply_to_id)
            elif isinstance(ret, str):
                room.send_text(ret)
    else:
        print(event['type'])
        print(dir(event))
        print(dir(room))


def onEvent(*args):
    log.info(f"onEvent: {args}")


def run():
    global cmds

    logging.basicConfig(level=logging.INFO)

    cfg = json.loads(open("config.json").read())
    mxcfg = cfg["matrix"]
    fcfg = cfg["fraenir"]

    cmds = CommandParser(mxcfg["user"])
    db.init(fcfg)

    kwargs = {"user_id": f"@{mxcfg['user']}:{mxcfg['homeserver']}",
              "encryption": mxcfg["encryption"]}
    if mxcfg["encryption"]:
        kwargs["restore_device_id"] = True
        kwargs["encryption_conf"] = {'db_path': os.path.dirname(mxcfg["db"]),
                                     'db_name': os.path.basename(mxcfg["db"]),
                                     'Store': FrCryptoStore}
    client = MatrixClient(mxcfg["homeserver"], **kwargs)
    token = client.login(mxcfg["user"], mxcfg["password"])
    client.add_listener(onEvent)

    try:
        for name in mxcfg["rooms"]:
            room = client.join_room(name)
            room.enable_encryption()
            log.info(f"Connected to room: {room.name} / {room.room_id}")
            room.add_listener(onMessage)
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
