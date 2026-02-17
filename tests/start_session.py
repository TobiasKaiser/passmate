# SPDX-FileCopyrightText: 2022 Tobias Kaiser <mail@tb-kaiser.de>
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from passmate.config import Config
from passmate.session import SessionStarter, TimeTestSession

def config(tmp_path, host_id="pytest", template_preset="Aaaaaaaaaaaaaa5"):
    tmp_path = Path(tmp_path)
    return Config({
        "primary_db": str(tmp_path / "local.pmdb"),
        "shared_folder": str(tmp_path / "sync"),
        "host_id": host_id,
        "template_preset": template_preset,
    })


def start_session(tmp_path, init: bool = False, passphrase="MyPassphrase", template_preset="Aaaaaaaaaaaaaa5"):
    return SessionStarter(config(tmp_path, template_preset=template_preset), passphrase, init,
        session_cls=TimeTestSession)
