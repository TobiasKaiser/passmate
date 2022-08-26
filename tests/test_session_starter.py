import pytest
from passmate.session import SessionException, SessionError
from .start_session import start_session

def test_session_minimal(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session.save()

def test_db_does_not_exist(tmp_path):
    with pytest.raises(SessionException, match="SessionError.DB_DOES_NOT_EXIST"):
        with start_session(tmp_path, init=False) as session:
            session.save()

def test_session_save_and_reopen(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session.save()

    with start_session(tmp_path, init=False) as session:
        session.save()


def test_session_no_save_on_init(tmp_path):
    with start_session(tmp_path, init=True) as session:
        pass

    with pytest.raises(SessionException, match="SessionError.DB_DOES_NOT_EXIST"):
        with start_session(tmp_path, init=False) as session:
            pass

def test_db_already_exists(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session.save()

    with pytest.raises(SessionException, match="SessionError.DB_ALREADY_EXISTS"):
        with start_session(tmp_path, init=True) as session:
            pass

def test_db_wrong_passphrase(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session.save()

    with pytest.raises(SessionException, match="SessionError.WRONG_PASSPHRASE"):
        with start_session(tmp_path, init=False, passphrase="Wrong") as session:
            pass    