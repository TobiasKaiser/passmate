# SPDX-FileCopyrightText: 2022 Tobias Kaiser <mail@tb-kaiser.de>
# SPDX-License-Identifier: Apache-2.0

import pytest
import json

from .start_session import start_session

from passmate.raw_db import RawDatabase, DatabaseException, RawDatabaseUpdate, FieldTuple
from passmate.session import SessionException, Record

json_obj_local = {
    "version": 2,
    "purpose": "primary",
    "records": {
        "RecordA":[
            ["meta", "path", "NewPath", 400],
            ["user", "password", "newPW", 400],
            ["user", "password", "abcd", 300],
            ["user", "email", "invalid@example.com", 200],
            ["user", "username", "name1", 100],
            ["meta", "path", "InitialPath", 100],
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
            ["meta", "path", "InitialPath", 100],
        ],
        "RecordC":[
            ["meta", "path", "AnotherRecord", 600],
        ]
    }
}

json_obj_remote_path_collision = {
    "version": 2,
    "purpose": "sync_copy",
    "records": {
        "RecordA":[
            ["user", "username", "newName", 500],
            ["user", "password", "abcd", 300],
            ["user", "email", "invalid@example.com", 200],
            ["user", "username", "name1", 100],
            ["meta", "path", "InitialPath", 100],
        ],
        "RecordD":[
            # Collides with path of RecordA set at time 400 in json_obj_local:
            ["meta", "path", "NewPath", 700], 
        ],
        "RecordE":[
            # Collides with path of RecordB set at time 400 in json_obj_local:
            ["meta", "path", "MyTestPath", 300], 
        ],
    }
}

json_obj_remote_corrupted = {
    "version": 2,
    "purpose": "sync_copy",
    "records": {
        "RecordA":[
            ["user", "username", "newName", 500],
            ["user", "password", "abcd", 300],
            ["user", "email", "CORRUPTED", 200],
            ["user", "username", "name1", 100],
            ["meta", "path", "InitialPath", 100],
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
            ["meta", "path", "NewPath", 400],
            ["user", "password", "newPW", 400],
            ["user", "password", "abcd", 300],
            ["user", "email", "invalid@example.com", 200],
            ["user", "username", "name1", 100],
            ["meta", "path", "InitialPath", 100],
        ],
        "RecordB":[
            ["meta", "path", "MyTestPath", 400],
        ],
        "RecordC":[
            ["meta", "path", "AnotherRecord", 600],
        ]
    }
}

def test_merge():
    db_local = RawDatabase.from_json(json.dumps(json_obj_local))
    db_remote = RawDatabase.from_json(json.dumps(json_obj_remote))
    db_expected = RawDatabase.from_json(json.dumps(json_obj_expected))

    applied_updates = db_local.merge(db_remote)

    expected_updates = [
        RawDatabaseUpdate(record_id='RecordA', field_tuple=FieldTuple(domain='user', field_name='username', field_value='newName', mtime=500)),
        RawDatabaseUpdate(record_id='RecordC', field_tuple=FieldTuple(domain='meta', field_name='path', field_value='AnotherRecord', mtime=600)),
    ]

    assert set(applied_updates) == set(expected_updates)

    #assert db_local.json() == db_expected.json()


def test_merge_corrupted():
    db_local = RawDatabase.from_json(json.dumps(json_obj_local))
    db_remote_corrupted = RawDatabase.from_json(json.dumps(json_obj_remote_corrupted))
    
    with pytest.raises(DatabaseException, match="two different field tuples with same mtime."):
        applied_updates = db_local.merge(db_remote_corrupted)

def test_merge_session(tmp_path):
    db_local = RawDatabase.from_json(json.dumps(json_obj_local))
    db_remote = RawDatabase.from_json(json.dumps(json_obj_remote))
    db_expected = RawDatabase.from_json(json.dumps(json_obj_expected))

    with start_session(tmp_path, init=True) as session:
        session.merge(db_local)
        assert set(iter(session)) == set(["NewPath", "MyTestPath"])
        assert session.reload_counter == 1

        applied_updates = session.merge(db_remote)
        assert applied_updates == [
            RawDatabaseUpdate(record_id='RecordA', field_tuple=FieldTuple(domain='user', field_name='username', field_value='newName', mtime=500)),
            RawDatabaseUpdate(record_id='RecordC', field_tuple=FieldTuple(domain='meta', field_name='path', field_value='AnotherRecord', mtime=600))
        ]

        assert set(iter(session)) == set(["NewPath", "MyTestPath", "AnotherRecord"])
        assert session["NewPath"]["username"] == "newName"
        assert session.reload_counter == 2


def test_merge_session_minimal(tmp_path):
    merge_in = RawDatabase()
    merge_in.update(RawDatabaseUpdate('RecordA', FieldTuple('meta', 'path', 'HelloWorld', 100)))
    with start_session(tmp_path, init=True) as session:
        session["asdf"] = Record()
        session.merge(merge_in)
        assert set(iter(session)) == set(["HelloWorld", "asdf"])


def test_merge_path_collision(tmp_path):
    # Nothing special happens on RawDatabase level when a path collision occurs.
    # This observation implies that this test case is not very useful.
    # Path collisions are handled and resolved on Session level, see 
    # test_merge_session_path_collision and test_merge_session_path_collision_exception.

    db_local = RawDatabase.from_json(json.dumps(json_obj_local))
    db_remote_path_collision = RawDatabase.from_json(json.dumps(json_obj_remote_path_collision))
    
    applied_updates = db_local.merge(db_remote_path_collision)

    expected_updates = [
        RawDatabaseUpdate(record_id='RecordA', field_tuple=FieldTuple(domain='user', field_name='username', field_value='newName', mtime=500)),
        RawDatabaseUpdate(record_id='RecordD', field_tuple=FieldTuple(domain='meta', field_name='path', field_value='NewPath', mtime=700)),
        RawDatabaseUpdate(record_id='RecordE', field_tuple=FieldTuple(domain='meta', field_name='path', field_value='MyTestPath', mtime=300))
    ]

    assert set(applied_updates) == set(expected_updates)


def test_merge_session_path_collision(tmp_path):
    db_local = RawDatabase.from_json(json.dumps(json_obj_local))
    db_remote_path_collision = RawDatabase.from_json(json.dumps(json_obj_remote_path_collision))
    
    with start_session(tmp_path, init=True) as session:
        session.current_time = 2000
        c = session.merge(db_local)
        c = session.merge(db_remote_path_collision)
        renamed_records = session.reload_records_if_invalid(fix_path_collisions=True)
        assert session.reload_counter == 1
        assert renamed_records == ["NewPath_", "MyTestPath_"]


def test_merge_session_path_collision_exception(tmp_path):
    db_local = RawDatabase.from_json(json.dumps(json_obj_local))
    db_remote_path_collision = RawDatabase.from_json(json.dumps(json_obj_remote_path_collision))
    
    with start_session(tmp_path, init=True) as session:
        session.current_time = 2000
        c = session.merge(db_local)
        c = session.merge(db_remote_path_collision)
        with pytest.raises(SessionException, match="SessionError.PATH_COLLISION"):
            renamed_records = session.reload_records_if_invalid(fix_path_collisions=False)
