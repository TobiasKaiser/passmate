import platform
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    primary_db: str
    shared_folder: str
    host_id: str

    @classmethod
    def default(cls):
        primary_db_default = str(Path.home() / ".local/share/passmate/local.pmdb")
        shared_folder_default = str(Path.home() / ".local/share/passmate/sync/")
        host_id_default = platform.node() # System's hostname
        return cls({
            "primary_db": primary_db_default,
            "shared_folder": shared_folder_default,
            "host_id": host_id_default,
        })

    def __init__(self, dict_data):
        object.__setattr__(self, "primary_db", dict_data["primary_db"])
        object.__setattr__(self, "shared_folder", dict_data["shared_folder"])
        object.__setattr__(self, "host_id", dict_data["host_id"])

    def dict(self):
        return {
            "primary_db": self.primary_db,
            "shared_folder": self.shared_folder,
            "host_id": self.host_id,
        }
