from pathlib import Path

from passmate.config import Config
from passmate.session import SessionStarter, TimeTestSession

def config(tmp_path, host_id="pytest"):
    tmp_path = Path(tmp_path)
    return Config({
        "primary_db": str(tmp_path / "local.pmdb"),
        "shared_folder": str(tmp_path / "sync"),
        "host_id": "pytest",
    })


def start_session(tmp_path, init: bool = False, passphrase="MyPassphrase"):
    return SessionStarter(config(tmp_path), passphrase, init,
        session_cls=TimeTestSession)
