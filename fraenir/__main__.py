import sys
import json
import logging
import ssl
import socks

import nio
from nio.client import HttpClient, TransportType
from nio.responses import ErrorResponse, LoginResponse

# from matrix_client.client import MatrixClient
# from matrix_client.api import MatrixRequestError
# from requests.exceptions import MissingSchema

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
            ret = cmds.parse(line)
            if ret is False:
                log.info("Logged")
                Message.log(MessageType.MSG, room, event["event_id"],
                            event["sender"], line, reply_to_id)
            elif isinstance(ret, str):
                room.send_text(ret)
    else:
        print(event['type'])


def onEvent(*args):
    log.info(f"onEvent: {args}")


def login(mxcfg, sock, client):
    _, data = client.login(mxcfg["password"])
    sock.sendall(data)

    response = None

    while not response:
        received_data = sock.recv(4096)
        client.receive(received_data)
        response = client.next_response()

    if isinstance(response, LoginResponse):
        log.info(response)
        log.info(response.access_token)
    elif isinstance(response, ErrorResponse):
        log.error(str(response))

    disconnect(sock, client)

    return True


def connect(mxcfg):
    context = ssl.create_default_context()

    if mxcfg["ssl_insecure"]:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    context.set_alpn_protocols(["h2", "http/1.1"])

    try:
        context.set_npn_protocols(["h2", "http/1.1"])
    except NotImplementedError:
        pass

    sock = socks.socksocket()

    if mxcfg["proxy"]:
        sock.set_proxy(mxcfg["proxy_type"], mxcfg["proxy"], mxcfg["proxy_port"])

    try:
        sock.connect((mxcfg["homeserver"], mxcfg["port"]))
    except socket.error as e:
        raise SystemExit(e)

    try:
        ssl_socket = context.wrap_socket(sock, server_hostname=mxcfg["homeserver"])
    except (ssl.SSLError, socket.error) as e:
        raise SystemExit(e)

    negotiated_protocol = ssl_socket.selected_alpn_protocol()
    if negotiated_protocol is None:
        negotiated_protocol = ssl_socket.selected_npn_protocol()

    transport_type = None

    if negotiated_protocol == "http/1.1":
        transport_type = TransportType.HTTP
    elif negotiated_protocol == "h2":
        transport_type = TransportType.HTTP2
    else:
        raise NotImplementedError

    client = HttpClient(mxcfg["homeserver"], mxcfg["user"])
    data = client.connect(transport_type)

    try:
        ssl_socket.sendall(data)
    except socket.error as e:
        raise SystemExit(e)

    return ssl_socket, client


def disconnect(sock, client):
    data = client.disconnect()
    sock.sendall(data)

    sock.shutdown(socket.SHUT_RDWR)
    sock.close()


def main():
    global cmds

    logging.basicConfig(level=logging.INFO)

    cfg = json.loads(open("config.json").read())
    mxcfg = cfg["matrix"]
    fcfg = cfg["fraenir"]

    cmds = CommandParser(mxcfg["user"])
    db.init(fcfg)

    sock, client = connect(mxcfg)
    login(mxcfg, sock, client)

    # client = MatrixClient(mxcfg["homeserver"],
    #                       user_id=f"@{mxcfg['user']}:{mxcfg['homeserver']}",
    #                       encryption=mxcfg["encryption"])
    # token = client.login(mxcfg["user"], mxcfg["password"])
    # client.add_listener(onEvent)

    # try:
    #     for name in mxcfg["rooms"]:
    #         room = client.join_room(name)
    #         log.info(f"Connected to room: {room.display_name} / {room.room_id}")
    #         room.add_listener(onMessage)
    # except MatrixRequestError as e:
    #     log.exception(e)
    #     if e.code == 400:
    #         log.warn("Room ID/Alias in the wrong format")
    #         sys.exit(11)
    #     else:
    #         log.warn("Couldn't find room.")
    #         sys.exit(12)

    # client.listen_forever()


if __name__ == "__main__":
    main()
