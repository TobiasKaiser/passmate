import json
from .read_passphrase import read_passphrase
from .container import load_encrypted
from .raw_db import FieldTuple, RawDatabaseUpdate
from .session import SessionStarter
from .config import Config

class MigrationException(Exception):
    pass

def value_list_to_str(value_list: list[str]) -> str:
    if len(value_list)==0:
        return None
    else:
        return "\n".join(value_list)

def translate_field_tuple(field_tuple_old) -> FieldTuple:
    combined_field_name = field_tuple_old[0]

    if combined_field_name == "PATH":
        domain="meta"
        field_name="path"
    elif combined_field_name == "SCHEMA":
        # Discard SCHEMA values
        return None
    elif combined_field_name[0] == "_":
        domain="user"
        field_name=combined_field_name[1:]
    else:
        raise MigrationException(f"Encountered unknwon combined_field_name \"{combined_field_name}\".")

    mtime = field_tuple_old[1]
    value_list = field_tuple_old[2:]

    return FieldTuple(
        domain=domain,
        field_name=field_name,
        field_value=value_list_to_str(value_list),
        mtime=mtime
    )

def migrate(src_filename, dest_filename):
    with open(src_filename, "rb") as f:
        head = f.read(6)
        is_scrypt_container = (head == b"scrypt")

    if is_scrypt_container:
        passphrase = read_passphrase(src_filename, open=True)
        data_str = load_encrypted(src_filename, passphrase)
    else:
        passphrase = ""
        with open(src_filename, "r") as f:
            data_str = f.read()
    data = json.loads(data_str)

    if data["version"] != 1:
        raise MigrationException(f"Input data has version {data['version']}, expected version 1.")

    if set(data.keys()) != set(["version", "records"]):
        raise MigrationException("Unexpected input data keys.")

    config = Config({
        "primary_db": dest_filename,
    })

    with SessionStarter(config, passphrase, init=True) as session:
        n_records = 0
        n_updates = 0
        for record_id, field_tuples_old in data["records"].items():
            for field_tuple_old in field_tuples_old:
                field_tuple_new = translate_field_tuple(field_tuple_old)
                if field_tuple_new==None:
                    continue
                u=RawDatabaseUpdate(record_id, field_tuple_new)
                #print("\t", u)
                session.update(u, invalidates_internal_repr=True)
                n_updates += 1
            n_records += 1
        
        session.save()

    print(f"Migrated {n_records} records with {n_updates} updates to {dest_filename}.")