from .config import Config
import fcntl
import os
import sys
from enum import Enum
import scrypt

from .container import save_encrypted, load_encrypted
from .raw_db import RawDatabase

class SessionError(Enum):
    DB_ALREADY_EXISTS = 1
    DB_DOES_NOT_EXIST = 2
    WRONG_PASSPHRASE = 3


class SessionException(Exception):
    def __init__(self, error: SessionError):
        self.error = error

    def __str__(self):
        return str(self.error)

class SessionStarter:
    """
    A wrapper for Session that implements locking and database creation.

    A separate lock file is used, as the database file itself is swapped out
    when it is written. Exclusive locking is done using lockf. The existence of
    the lock file itself does not consititute a lock.
    """
    def __init__(self, config: Config, passphrase: str, init: bool = False):
        """
        Args:
            config: Config object read from user's config.toml
            passphrase: Passphrase to de- and encrypt database. When init is
                False, this must match the previously chosen passphrase. When
                init is True, an initial passphrase must be provided.
            init: Set to True to create a new database.
        """
        self.config = config
        self.passphrase = passphrase
        self.init = init
        self.has_lock = False

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
                # TODO: Raise DB_DOES_NOT_EXIST on FileNotFoundError here.

            s = Session(self.config, self.passphrase, db)
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

        self.save()

    def save(self):
        data = self.db.json()
        save_encrypted(self.config.primary_db, self.passphrase, data)