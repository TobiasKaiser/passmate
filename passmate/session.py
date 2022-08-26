import fcntl
import os
import sys
import scrypt
import secrets
import collections
import time
import base64
from enum import Enum
from pathlib import Path

from .config import Config
from .container import save_encrypted, load_encrypted
from .raw_db import RawDatabase, RawRecord, FieldTuple, RawDatabaseUpdate
from .pathtree import PathTree

class SessionError(Enum):
    DB_ALREADY_EXISTS = 1
    DB_DOES_NOT_EXIST = 2
    WRONG_PASSPHRASE = 3
    UNBOUND_RECORD_ACCESS = 4
    MTIME_IN_THE_FUTURE = 5
    PATH_COLLISION = 6

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

    def invalidate(self):
        """
        Invalidating a Record unbinds it from its Session.
        """
        assert self.session
        assert self._bound
        self._bound = False
        self.session = None

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

    def __len__(self) -> int:
        return len(self._userdata)

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
        self.session.update(RawDatabaseUpdate(self.record_id, field_tuple), invalidates_internal_repr=False)

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

class SyncSummary:
    def __init__(self):
        # Key: Path, Value: error message
        self.failure = {}
        # Key: Path, Value: list of RawDatabaseUpdates
        self.success = {}

    def __repr__(self):
        return f"SyncSummary(failure={self.failure}, success={self.success})"

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
            db: RawDatabase read from file or None to initialize a new DB.
        """
        self.config = config
        self.passphrase = passphrase
        if db:
            self.db = db
            self.save_required = False
        else:
            self.db = RawDatabase()
            self.save_required = True

        self._records = {}
        self._records_valid = False
        self.reload_counter = 0
        self.tree = PathTree(self)


    def set_passphrase(self, passphrase):
        self.passphrase = passphrase
        self.save_required = True

    def invalidate(self):
        """
        Invalidates internal representation, including all Records and the PathTree.
        """
        if self._records_valid:
            for record in self._records.values():
                record.invalidate()
            self._records_valid = False
        
        self.tree.invalidate()

    def reload_records_if_invalid(self, fix_path_collisions:bool=False) -> list[str]:
        """
        Args:
            fix_path_collisions: Fix path collisions. This should only be
                necessary after a database was merged. The record order in the
                underlying RawDatabase determines which Record keeps its name
                and whose Record name is changed. This record oder is more or
                less arbitrary.

        Returns:
            List containing new path of each record whose path was fixed.
            If fix_path_collisions is False, this list is always empty.
        """
        if self._records_valid:
            return []

        fixed_paths = []
        self._records = {}
        for record_id, raw_record in self.db.records.items():
            r = Record(record_id)
            r.register_session_load(self, raw_record)
            path = r.path()
            if not path: # Ignore deleted records (path is None / null).
                continue
            rename_required = False
            while path in self._records:
                path += "_" # Append underscores until we have an unused path.
                rename_required = True
            if rename_required:
                if fix_path_collisions:
                    r.update_rename(path)
                    fixed_paths.append(path)
                else:
                    raise SessionException(SessionError.PATH_COLLISION)
            
            assert not (path in self._records)
            self._records[path] = r

        self._records_valid = True
        self.reload_counter += 1
        return fixed_paths

    def __iter__(self):
        """
        Iterates over record paths.
        """
        self.reload_records_if_invalid()

        return iter(self._records)

    def __setitem__(self, path, rec):
        """
        To create a new record: sess["NewPath"] = Record()
        To rename a record: sess["NewPath"] = sess["OldPath"]
        (old path is automatically deleted)
        """
        self.reload_records_if_invalid()

        assert isinstance(rec, Record)
        assert len(path) > 0
        if path in self._records:
            raise SessionException(SessionError.PATH_COLLISION)

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

        self.tree.invalidate()

    def __delitem__(self, path):
        self.reload_records_if_invalid()

        rec = self._records[path]
        rec.update_delete()
        del self._records[path]

        self.tree.invalidate()


    def __getitem__(self, path):
        self.reload_records_if_invalid()

        return self._records[path]

    def update(self, u: RawDatabaseUpdate, invalidates_internal_repr) -> bool:
        """
        Directly applies the RawDatabaseUpdate u to the underlying RawDatabase.

        Args:
            u: RawDatabaseUpdate
            invalidates_internal_repr: True if the update would invalidate the
                internal _records representation (i. e. merge operation).
                False, if the internal _records representation remains valid.

        Returns:
            True, if the change was applied.
        """

        updated = self.db.update(u, ignore_existing=True)

        if updated:
            if invalidates_internal_repr:
                self.invalidate()
            self.save_required = True
            return True
        else:
            return False

    def _sync_single_file(self, summary: SyncSummary, fn: Path):
        """
        Loads sync copy from fn and appends result to summary.
        """

        try:
            data = load_encrypted(fn, self.passphrase)
            remote_db = RawDatabase.from_json(data)
        except scrypt.error as e:
            if e.args[0] == "password is incorrect":
                summary.failure[fn] = "Passphrase incorrect."
                return
            else:
                raise e

        updates_applied = self.merge(remote_db)
        summary.success[fn] = updates_applied

    def sync(self) -> SyncSummary:
        summary = SyncSummary()

        for fn in self.config.shared_folder.iterdir():
            if fn.suffix != ".pmdb":
                continue

            if fn.stem == self.config.host_id:
                continue # Ignore own output

            self._sync_single_file(summary, fn)
        return summary

    def _save_primary_db(self):        
        data = self.db.json()
        save_encrypted(self.config.primary_db, self.passphrase, data)

    def _save_sync_copy(self):
        if self.config.shared_folder and self.config.host_id:
            self.config.shared_folder.mkdir(parents=True, exist_ok=True)
            sync_copy_filename = self.config.shared_folder / f"{self.config.host_id}.pmdb"
            sync_copy_data = self.db.json(purpose="sync_copy")
            save_encrypted(sync_copy_filename, self.passphrase, sync_copy_data)

    def save(self):
        """
        Saves changes if necessary.
        Returns:
            True if unsaved changes were saved.
        """

        if self.save_required:
            self._save_primary_db()
            self._save_sync_copy()

            self.save_required = False
            return True
        return False

    def merge(self, remote_db: RawDatabase) -> list[RawDatabaseUpdate]:
        """
        Merge appends changes to pending updates.

        Returns:
            List of applied updates.
        """

        proposed_updates = self.db.merge(remote_db)
        #updated = [self.update(u, invalidates_internal_repr=True) for u in proposed_updates]
        #return any(updated)
        applied_updates = list(filter(lambda u: self.update(u, invalidates_internal_repr=True), proposed_updates))
        return applied_updates

    def time(self):
         return int(time.time())

class TimeTestSession(Session):
    """
    Like session, but uses an incrementing time variable instead of real UNIX
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
                db = None # => init
            else:
                try:
                    data = load_encrypted(self.config.primary_db, self.passphrase)
                except scrypt.error as e:
                    if e.args[0] == "password is incorrect":
                        raise SessionException(SessionError.WRONG_PASSPHRASE) from e
                    else:
                        raise e
                except FileNotFoundError as e:
                    raise SessionException(SessionError.DB_DOES_NOT_EXIST) from e
                else:
                    db = RawDatabase.from_json(data)

            return self.session_cls(self.config, self.passphrase, db)
        except:
            # Make sure that we release the lock if an exception occurs after
            # acquire_lock:
            if self.__exit__(*sys.exc_info()):
                pass
            else:
                raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_lock()
