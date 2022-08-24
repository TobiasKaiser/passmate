from .config import Config
import fcntl
import os
import sys
from enum import Enum
import scrypt
import secrets
import collections
import time
import base64

from .container import save_encrypted, load_encrypted
from .raw_db import RawDatabase, RawRecord, FieldTuple

DatabaseUpdate = collections.namedtuple(
    "DatabaseUpdate", ["record_id", "field_tuple"])

class SessionError(Enum):
    DB_ALREADY_EXISTS = 1
    DB_DOES_NOT_EXIST = 2
    WRONG_PASSPHRASE = 3
    UNBOUND_RECORD_ACCESS = 4
    MTIME_IN_THE_FUTURE = 5

class SessionException(Exception):
    def __init__(self, error: SessionError):
        self.error = error

    def __str__(self):
        return str(self.error)


def random_key():
    return base64.b16encode(secrets.token_bytes(8)).decode("ascii")


class Record:
    """
    After instantiating a Record, it must be bound to a Session by assigning it
    to a session as item::

        s["myrecord"] = Record()

    Before such an assignment, the Record is "unbound" and cannot be used.
    Internally, this assignment triggers register_session_create, which binds
    the Record to the Session.

    When Session reads a DB from file, all contained Records are bound using
    the register_session_load method.
    """

    def __init__(self, record_id=None):
        """
        

        Args:
            record_id: Either an existing ID or None to create a new record with
                random ID.
        """

        self.session = None

        if record_id:
            self.record_id = record_id
            self.creation_pending = False
        else:
            self.record_id = random_key()
            self.creation_pending = True

        self._path = ""
        self._userdata = {}
        self._path_mtime = 0
        self._userdata_mtime = {}

        self._bound = False
    

    def register_session_load(self, session, raw_record):
        """
        When reading a DB from file, Session loads and binds records using
        this method.
        """
        assert not self._bound
        assert not self.creation_pending

        self.session = session
        for ft in raw_record:
            self._load_field_tuple(ft)

        self._bound = True

    def register_session_create(self, session, path):
        """
        Triggered by Session on assignment to an item, such as::

            s["myrecord"] = Record()
        """
        assert not self._bound
        assert self.creation_pending
        
        self.session = session
        init_ft = FieldTuple("meta", "path", path, self.session.time())
        self._load_field_tuple(init_ft)
        self._add_update(init_ft)

        self.creation_pending = False
        self._bound = True

    def _load_field_tuple(self, ft: FieldTuple):
        if ft.domain == "meta":
            if ft.field_name == "path":
                if ft.mtime > self._path_mtime:
                    self._path = ft.field_value
                    self._path_mtime = ft.mtime
            else:
                assert False
        elif ft.domain == "user":
            if ft.mtime > self.field_mtime(ft.field_name):
                if ft.field_value:
                    self._userdata[ft.field_name] = ft.field_value
                else:
                    try:
                        del self._userdata[ft.field_name]
                    except KeyError:
                        pass
                self._userdata_mtime[ft.field_name] = ft.mtime
        else:
            assert False

    def field_mtime(self, field_name):
        try:
            return self._userdata_mtime[field_name]
        except KeyError:
            return 0

    def __repr__(self):
        return f"Record(path={self.path()}, data={self._userdata})"

    def path(self) -> str:
        return self._path
        
    def __iter__(self) -> str:
        """
        Iterates over use data field names.
        """

        if not self._bound:
            raise SessionException(SessionError.UNBOUND_RECORD_ACCESS)

        return iter(self._userdata)

    def __setitem__(self, field_name, value):
        if not self._bound:
            raise SessionException(SessionError.UNBOUND_RECORD_ACCESS)

        if (field_name in self._userdata) and (self._userdata[field_name] == value):
            return

        self._update_set_field(field_name, value)


    def __delitem__(self, field_name):
        if not self._bound:
            raise SessionException(SessionError.UNBOUND_RECORD_ACCESS)

        self._update_set_field(field_name, None)

    def __getitem__(self, field_name):
        if not self._bound:
            raise SessionException(SessionError.UNBOUND_RECORD_ACCESS)

        return self._userdata[field_name]

    def _add_update(self, field_tuple: FieldTuple):
        self.session.pending_updates.append(DatabaseUpdate(
            self.record_id, field_tuple))

    def update_delete(self):
        self.update_rename(new_path=None)

    def update_rename(self, new_path):
        cur_time = self.session.time()
        if cur_time <= self._path_mtime:
            raise SessionException(SessionError.MTIME_IN_THE_FUTURE)
        
        ft = FieldTuple("meta", "path", new_path, cur_time)
        self._add_update(ft)
        
        self._path_mtime = cur_time
        self._path = new_path

    def _update_set_field(self, field_name, value):
        cur_time = self.session.time()
        if cur_time <= self.field_mtime(field_name):
            raise SessionException(SessionError.MTIME_IN_THE_FUTURE)

        ft = FieldTuple("user", field_name, value, cur_time)
        self._add_update(ft)

        if value:
            self._userdata[field_name] = value
        else:
            del self._userdata[field_name]
        self._userdata_mtime[field_name] = cur_time

class Session:
    """
    Use SessionStarter and 'with' to obtain a Session object.

    The Session object is used to access a primary database file for both
    read and write operations. The Session object also manages synchronization
    using synchronization copies and a shared folder.

    Any component that provides a user interface for Passmate should create
    one Session instance. Interactive interfaces should keep the Session open
    and close it only when the interactive session has ended.
    """
    
    def __init__(self, config: Config, passphrase: str, db: RawDatabase):
        """
        A Session object is created by SessionStarter, once a lock on the DB
        has been acquired and either DB existence and correct passphrase has
        been established or a new DB has been initialized.

        Args:
            config: Config object read from user's config.toml
            passphrase: Passphrase to de- and encrypt database.
                At this point, it must be the actual passphrase and cannot be
                a password entry attempt anymore (handled by SessionStarter).
            db: RawDatabase read from file or newly initialized RawDatabase.
        """
        self.config = config
        self.passphrase = passphrase
        self.db = db
        self.reload_records()
        self.pending_updates = []
        #self.save()

    def reload_records(self):
        self._records = {}
        for record_id, raw_record in self.db.records.items():
            r = Record(record_id)
            r.register_session_load(self, raw_record)
            path = r.path()
            if not path:
                continue
            self._records[path] = r

    def __iter__(self):
        """
        Iterates over record paths.
        """
        return iter(self._records)

    def __setitem__(self, path, rec):
        """
        To create a new record: sess["NewPath"] = Record()
        To rename a record: sess["NewPath"] = sess["OldPath"]
        (old path is automatically deleted)
        """
        assert isinstance(rec, Record)
        assert len(path) > 0

        if rec.creation_pending:
            rec.register_session_create(self, path)
            assert rec.path() == path
            self._records[path] = rec
        else:
            old_path = rec.path()
            assert rec.session == self
            assert self._records[old_path] == rec
            rec.update_rename(path)
            
            self._records[path] = rec
            del self._records[old_path]

    def __delitem__(self, path):
        rec = self._records[path]
        rec.update_delete()
        del self._records[path]


    def __getitem__(self, path):
        return self._records[path]

    def apply_updates(self):
        updates_applied = 0
        while len(self.pending_updates) > 0:
            record_id, field_tuple = self.pending_updates.pop()
            if not record_id in self.db.records:
                self.db.records[record_id] = RawRecord()
            self.db.records[record_id].append(field_tuple)
            updates_applied += 1
        return updates_applied > 0

    def save(self, force=False):
        """
        Args:
            force: save even when there are no updates pending.
        """
        update_required = self.apply_updates()
        if update_required or force:
            data = self.db.json()
            save_encrypted(self.config.primary_db, self.passphrase, data)

    def time(self):
         return int(time.time())

class TimeTestSession(Session):
    """
    Like session, but uses a incrementing time variable instead of real UNIX
    time. For testing purposes only.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_time = 0


    def time(self):
        self.current_time+=1
        return self.current_time


class SessionStarter:
    """
    A wrapper for Session that implements locking and database creation.

    A separate lock file is used, as the database file itself is swapped out
    when it is written. Exclusive locking is done using lockf. The existence of
    the lock file itself does not consititute a lock.
    """
    def __init__(self, config: Config, passphrase: str, init: bool = False, session_cls: type = Session):
        """
        Args:
            config: Config object read from user's config.toml
            passphrase: Passphrase to de- and encrypt database. When init is
                False, this must match the previously chosen passphrase. When
                init is True, an initial passphrase must be provided.
            init: Set to True to create a new database.
            session_cls: Session class to instantiate. Can be Session or TimeTestSession.
        """
        self.config = config
        self.passphrase = passphrase
        self.init = init
        self.has_lock = False
        self.session_cls = session_cls

    def lock_filename(self):
        db_fn = self.config.primary_db
        return db_fn.with_suffix(db_fn.suffix+".lock")

    def acquire_lock(self):
        assert not self.has_lock
        self.lockfile = open(self.lock_filename(), "w")
        fcntl.lockf(self.lockfile, fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.has_lock = True

    def release_lock(self):
        assert self.has_lock
        self.has_lock = False
        os.unlink(self.lock_filename())
        self.lockfile.close()

    def __enter__(self):
        self.acquire_lock()
        try:
            if self.init:
                if self.config.primary_db.exists():
                    raise SessionException(SessionError.DB_ALREADY_EXISTS)
                db = RawDatabase()
            else:
                try:
                    data = load_encrypted(self.config.primary_db, self.passphrase)
                    db = RawDatabase.from_json(data)
                except scrypt.error as e:
                    if e.args[0] == "password is incorrect":
                        raise SessionException(SessionError.WRONG_PASSPHRASE) from e
                    else:
                        raise e
                except FileNotFoundError as e:
                    raise SessionException(SessionError.DB_DOES_NOT_EXIST) from e

            s = self.session_cls(self.config, self.passphrase, db)
            if self.init:
                s.save(force=True)
            return s
        except:
            # Make sure that we release the lock if an exception occurs after
            # acquire_lock:
            if self.__exit__(*sys.exc_info()):
                pass
            else:
                raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_lock()
