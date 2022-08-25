import pytest
import json

from passmate.raw_db import RawDatabase, DatabaseException, RawDatabaseUpdate, FieldTuple

def test_merge():
    json_obj_local = {
        "version": 2,
        "purpose": "primary",
        "records": {
            "RecordA":[
                ["user", "password", "newPW", 400],
                ["user", "password", "abcd", 300],
                ["user", "email", "invalid@example.com", 200],
                ["user", "username", "name1", 100],
            ],
            "RecordB":[
                ["meta", "path", "MyTestPath", 400],
            ]
        }
    }

    json_obj_remote = {
        "version": 2,
        "purpose": "sync_copy",
        "records": {
            "RecordA":[
                ["user", "username", "newName", 500],
                ["user", "password", "abcd", 300],
                ["user", "email", "invalid@example.com", 200],
                ["user", "username", "name1", 100],
            ],
            "RecordC":[
                ["meta", "path", "AnotherRecord", 600],
            ]
        }
    }

    json_obj_expected = {
        "version": 2,
        "purpose": "primary",
        "records": {
            "RecordA":[
                ["user", "username", "newName", 500],
                ["user", "password", "newPW", 400],
                ["user", "password", "abcd", 300],
                ["user", "email", "invalid@example.com", 200],
                ["user", "username", "name1", 100],
            ],
            "RecordB":[
                ["meta", "path", "MyTestPath", 400],
            ],
            "RecordC":[
                ["meta", "path", "AnotherRecord", 600],
            ]
        }
    }


    db_local = RawDatabase.from_json(json.dumps(json_obj_local))
    db_remote = RawDatabase.from_json(json.dumps(json_obj_remote))
    db_expected = RawDatabase.from_json(json.dumps(json_obj_expected))

    applied_updates = db_local.merge(db_remote)

    expected_updates = [
        RawDatabaseUpdate(record_id='RecordA', field_tuple=FieldTuple(domain='user', field_name='username', field_value='newName', mtime=500)),
        RawDatabaseUpdate(record_id='RecordC', field_tuple=FieldTuple(domain='meta', field_name='path', field_value='AnotherRecord', mtime=600)),
    ]

    assert set(applied_updates) == set(expected_updates)

    assert db_local.json() == db_expected.json()
