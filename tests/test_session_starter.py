import pytest
from pathlib import Path
from passmate.session import SessionStarter, SessionException, SessionError
from passmate.config import Config

def config(tmp_path, host_id="pytest"):
    tmp_path = Path(tmp_path)
    return Config({
        "primary_db": str(tmp_path / "local.pmdb"),
        "shared_folder": str(tmp_path / "sync"),
        "host_id": "pytest",
    })

def test_session_minimal(tmp_path):
    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=True) as session:
        session.save()

def test_db_does_not_exist(tmp_path):
    with pytest.raises(SessionException, match="SessionError.DB_DOES_NOT_EXIST"):
        with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=False) as session:
            session.save()

def test_session_save_and_reopen(tmp_path):
    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=True) as session:
        session.save()

    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=False) as session:
        session.save()


def test_session_save_on_init(tmp_path):
    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=True) as session:
        pass

    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=False) as session:
        session.save()

def test_db_already_exists(tmp_path):
    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=True) as session:
        session.save()

    with pytest.raises(SessionException, match="SessionError.DB_ALREADY_EXISTS"):
        with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=True) as session:
            pass

def test_db_wrong_passphrase(tmp_path):
    with SessionStarter(config(tmp_path), passphrase="MyPassphrase", init=True) as session:
        session.save()

    with pytest.raises(SessionException, match="SessionError.WRONG_PASSPHRASE"):
        with SessionStarter(config(tmp_path), passphrase="Wrong", init=False) as session:
            pass    