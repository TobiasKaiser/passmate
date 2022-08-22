import pytest
from passmate.session import SessionStarter, SessionException, SessionError, Record

from .start_session import start_session


def test_new_del_rename(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session["test1"] = Record()
        session["delete_me"] = Record()
        session["rename_me"] = Record()
        assert set(iter(session)) == set(["test1", "delete_me", "rename_me"])
        session["test2"] = session["rename_me"]
        assert set(iter(session)) == set(["test1", "delete_me", "test2"])
        
        del session["delete_me"]

        assert set(iter(session)) == set(["test1", "test2"])

        session.save()

    with start_session(tmp_path, init=False) as session:
        assert set(iter(session)) == set(["test1", "test2"])
