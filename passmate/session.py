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

class SessionException(Exception):
    def __init__(self, error: SessionError):
        self.error = error

    def __str__(self):
        return str(self.error)


def random_key():
    return base64.b16encode(secrets.token_bytes(8)).decode("ascii")


class Record:
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
        
    def register_session(self, session):
        assert not self.session
        self.session = session

    def load_from_raw_record(self, raw_record):
        self._path = ""
        self._userdata = {}
        path_mtime = 0
        userdata_mtime = {}
        for ft in raw_record: # Iterate over FieldTuples
            if ft.domain == "meta":
                if ft.field_name == "path":
                    if ft.mtime > path_mtime:
                        self._path = ft.field_value
                        path_mtime = ft.mtime
                else:
                    assert False
            elif ft.domain == "user":
                try:
                    prev_mtime = userdata_mtime[ft.field_name]
                except KeyError:
                    prev_mtime = 0
                if ft.mtime > prev_mtime:
                    self._userdata[ft.field_name] = ft.field_value
                    userdata_mtime[ft.field_name] = ft.mtime
            else:
                assert False

    def __repr__(self):
        return f"Record(path={self.path()}, data={self._userdata})"

    #def reload(self):
    #    db = self.session.db
    #    raw_record = db.records[self.record_id]
    #    self.load_from_raw_record(raw_record)


    def path(self) -> str:
        return self._path
        
    def __iter__(self) -> str:
        """
        Iterates over use data field names.
        """
        return iter(self._userdata)

    def __setitem__(self, key, value):
        if (key in self._userdata) and (self._userdata[key] == "value"):
            return

        self._userdata[key] = value

        self.update_setf

    def __getitem__(self, key):
        return self._userdata[key]

    def add_update(self, field_tuple: FieldTuple):
        self.session.pending_updates.append(DatabaseUpdate(
            self.record_id, field_tuple))

    def update_create(self, path):
        assert self.creation_pending

        init_ft = FieldTuple("meta", "path", path, self.session.time())
        self.load_from_raw_record([init_ft])
        self.add_update(init_ft)

        self.creation_pending = False

    def update_delete(self):
        self.update_rename(new_path=None)

    def update_rename(self, new_path):
        ft = FieldTuple("meta", "path", new_path, self.session.time())
        self.add_update(ft)
        self._path = new_path


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
            r.load_from_raw_record(raw_record)
            r.register_session(self)
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
            rec.register_session(self)
            rec.update_create(path)
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
