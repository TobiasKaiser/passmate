import pytest
from passmate.session import SessionStarter, SessionException, SessionError, Record

from .test_session_starter import config


def test_session_minimal(tmp_path):
    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=True) as session:
        session["test1"] = Record()
        session["delete_me"] = Record()
        session["rename_me"] = Record()
        assert set(iter(session)) == set(["test1", "delete_me", "rename_me"])
        session["test2"] = session["rename_me"]
        assert set(iter(session)) == set(["test1", "delete_me", "test2"])
        
        del session["delete_me"]

        assert set(iter(session)) == set(["test1", "test2"])

        session.save()

    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=False) as session:
        for path in session:
            print(session[path])

        assert set(iter(session)) == set(["test1", "test2"])
        #paths = list(iter(session))
        #assert len(paths) == 1 and "test" in paths
