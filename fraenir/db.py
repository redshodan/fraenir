import logging

from pysqlcipher3 import dbapi2
from matrix_client.crypto.crypto_store import CryptoStore

import sqlalchemy
from sqlalchemy import (create_engine, Column, Integer, ForeignKey, String,
                        DateTime, Sequence)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relation
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


def namedcache(klass):
    def load(session):
        for name in klass.__NC_preload__:
            if not (session.query(klass).
                    filter(klass.name == name).one_or_none()):
                session.add(klass(name=name))
        session.flush()
        for t in session.query(klass).all():
            klass.__NC_cache__[t.name] = t.id

    def lookup(session, name, **kwargs):
        if name in klass.cache:
            return klass.cache[name]
        else:
            kwargs[name] = name
            obj = klass(**kwargs)
            session.add(obj)
            session.flush()
            return obj.id

    if not hasattr(klass, "__NC_preload__"):
        klass.__NC_preload__ = []
    klass.__NC_cache__ = {}
    klass.load = load
    klass.lookup = lookup
    return klass


@namedcache
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, Sequence('users_id_seq'), primary_key=True)
    name = Column(String, unique=True)


@namedcache
class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, Sequence('rooms_id_seq'), primary_key=True)
    room_id = Column(String, unique=True)
    name = Column(String)


@namedcache
class MessageType(Base):
    __tablename__ = "msgtypes"
    __NC_preload__ = ["message", "url"]

    id = Column(Integer, Sequence('messages_id_seq'), primary_key=True)
    name = Column(String, nullable=False, unique=True)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, Sequence('messages_id_seq'), primary_key=True)
    type_id = Column(Integer, ForeignKey("msgtypes.id"))
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete='CASCADE'),
                     nullable=False)
    event_id = Column(String, nullable=False)
    from_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'),
                     nullable=False)
    tstamp = sqlalchemy.Column(DateTime, nullable=False)
    body = Column(String, nullable=False)
    reply_to_event_id = Column(String, nullable=True)

    type = relation("MessageType")

    @staticmethod
    def log(mt_name, room, event_id, from_id, tstamp, body,
            reply_to_event_id=None):
        with session_scope() as session:
            mt_id = MessageType.lookup(session, mt_name)
            r_id = Room.lookup(session, room.name, room_id=room.room_id)
            f_id = User.lookup(session, from_id)
            msg = Message(type_id=mt_id, room_id=r_id,
                          event_id=event_id, from_id=f_id, tstamp=tstamp,
                          body=body, reply_to_event_id=reply_to_event_id)
            session.add(msg)
            session.commit()


# Wrapper to force matrix_client CryptoStore to use the sqlcipher db
class FrCryptoStore(CryptoStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def instanciate_connection(self):
        con = dbapi2.connect(
            self.db_filepath, detect_types=dbapi2.PARSE_DECLTYPES)
        con.row_factory = dbapi2.Row
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
        MessageType.load(session)
