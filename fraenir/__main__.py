import sys
import json
import logging

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError
from requests.exceptions import MissingSchema

from .commands import CommandParser
from . import db
from .db import User, Room, MessageType, Message


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
            if cmds.parse(line) is False:
                log.info("Logged")
                Message.log(MessageType.MSG, room, event["event_id"],
                            event["sender"], line, reply_to_id)
    else:
        print(event['type'])


def run():
    global cmds

    logging.basicConfig(level=logging.INFO)

    cfg = json.loads(open("config.json").read())
    mxcfg = cfg["matrix"]
    fcfg = cfg["fraenir"]

    cmds = CommandParser(mxcfg["user"])
    db.init(fcfg)

    client = MatrixClient(mxcfg["homeserver"],
                          user_id=f"@{mxcfg['user']}:{mxcfg['homeserver']}",
                          encryption=mxcfg["encryption"])
    token = client.login(mxcfg["user"], mxcfg["password"])

    try:
        for name in mxcfg["rooms"]:
            room = client.join_room(name)
            log.info(f"Connected to room: {room.display_name} / {room.room_id}")
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
