from enum import Enum
import logging

from pysqlcipher3 import dbapi2
from matrix_client.crypto.crypto_store import CryptoStore

import sqlalchemy
from sqlalchemy import (create_engine, Table, Column, Integer, Text, ForeignKey,
                        String, DateTime, Index, Boolean, UniqueConstraint,
                        Sequence)
from sqlalchemy.engine import Engine
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relation
from sqlalchemy.orm.exc import NoResultFound
from contextlib import contextmanager


log = logging.getLogger(__name__)

Base = declarative_base()
Session = sessionmaker()
engine = None
db_file = None
db_pass = None


@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, Sequence('users_id_seq'), primary_key=True)
    name = Column(String, unique=True)

    cache = {}

    @staticmethod
    def load(session):
        for u in session.query(User).all():
            User.cache[u.name] = u.id

    @staticmethod
    def lookup(session, name):
        if name in User.cache:
            return User.cache[name]
        else:
            u = User(name=name)
            session.add(u)
            session.flush()
            User.cache[name] = u.id
            return u.id


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, Sequence('rooms_id_seq'), primary_key=True)
    room_id = Column(String, unique=True)
    name = Column(String)

    cache = {}

    @staticmethod
    def load(session):
        for r in session.query(Room).all():
            Room.cache[r.room_id] = r.id

    @staticmethod
    def lookup(session, room):
        if room.room_id in Room.cache:
            return Room.cache[room.room_id]
        else:
            r = Room(room_id=room.room_id, name=room.name)
            session.add(r)
            session.flush()
            Room.cache[room.room_id] = r.id
            return r.id


class MessageType(Enum):
    MSG = 1
    URL = 2


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, Sequence('messages_id_seq'), primary_key=True)
    type = Column(SQLEnum(MessageType), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete='CASCADE'),
                     nullable=False)
    event_id = Column(String, nullable=False)
    from_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'),
                     nullable=False)
    body = Column(String, nullable=False)
    reply_to_event_id = Column(String, nullable=True)

    @staticmethod
    def log(type, room, event_id, from_id, body, reply_to_event_id=None):
        with session_scope() as session:
            r_id = Room.lookup(session, room)
            f_id = User.lookup(session, from_id)
            msg = Message(type=type, room_id=r_id, event_id=event_id,
                          from_id=f_id, body=body,
                          reply_to_event_id=reply_to_event_id)
            session.add(msg)
            session.commit()


class FrCryptoStore(CryptoStore):
    def __init__(self, *args, **kwargs):
        print("FrCryptoStore.__init__", args, kwargs)
        super().__init__(*args, **kwargs)

    def instanciate_connection(self):
        print("connecting cryptostore to db")
        con = dbapi2.connect(
            self.db_filepath, detect_types=dbapi2.PARSE_DECLTYPES)
        con.row_factory = dbapi2.Row
        print("Sending key to db")
        con.executescript(f"PRAGMA KEY = '{db_pass}';")
        return con


def init(mbcfg):
    global engine, db_file, db_pass
    db_file = mbcfg['db']
    db_pass = mbcfg['passphrase']
    log.info(f"Connecting to db: {db_file}")
    engine = create_engine(f"sqlite+pysqlcipher://:{db_pass}@/{db_file}")
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)
    with session_scope() as session:
        User.load(session)
        Room.load(session)
