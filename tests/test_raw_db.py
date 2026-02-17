import pytest
import json
import jsonschema

from passmate.raw_db import RawDatabase, RawRecord, FieldTuple, DatabaseException, RawDatabaseUpdate


@pytest.mark.parametrize("purpose", ["primary", "sync_copy"])
def test_encode_json(purpose):
    db = RawDatabase()
    db.records["RecordA"] = RawRecord([
        FieldTuple("user", "email", "invalid@example.com", 123),
        FieldTuple("user", "password", "abcd", 124),
        FieldTuple("user", "password", "xyz", 5678),
    ])

    expected_obj = {
        "version": 2,
        "purpose": purpose,
        "records": {
            "RecordA":[
                ["user", "email", "invalid@example.com", 123],
                ["user", "password", "abcd", 124],
                ["user", "password", "xyz", 5678]
            ]
        }
    }
    generated_obj = json.loads(db.json(purpose=purpose))
    assert generated_obj == expected_obj

@pytest.mark.parametrize("purpose", ["primary", "sync_copy"])
def test_decode_json(purpose):
    input_json_obj = {
        "version": 2,
        "purpose": purpose,
        "records": {
            "RecordA":[
                ["user", "password", None, 5679],
                ["user", "password", "xyz", 5678],
                ["user", "password", "abcd", 124],
                ["user", "email", "invalid@example.com", 123],
            ],
            "RecordB":[
                ["meta", "path", "MyTestPath", 123456],
            ]
        }
    }
    input_json = json.dumps(input_json_obj)
    db = RawDatabase.from_json(input_json)

    if purpose == "primary":
        assert not db.is_sync_copy
        generated_obj = json.loads(db.json())
        assert generated_obj == input_json_obj
    elif purpose == "sync_copy":
        # If we load a sync copy, it should not be possible to save it again as JSON
        assert db.is_sync_copy
        with pytest.raises(DatabaseException):
            db.json()
    else:
        assert False


invalid_json_objs = [
    # Empty object:
    {},
    # Invalid purpose:
    {"version": 2, "purpose": "blabla", "records": {}},
    # Invalid version:
    {"version": 3, "purpose": "sync_copy", "records": {}},
    # No version:
    {"purpose": "sync_copy", "records": {}},
    # No purpose:
    {"version": 2, "records": {}},
    # No records:
    {"purpose": "primary", "version": 2},
    # Too many attributes:
    {"purpose": "primary", "version": 2, "records": {}, "hello":"world"},
    # record contains string instead of array of tuples:
    {"purpose": "primary", "version": 2, "records":{"RecA":"hello"}},
    # record contains array of string instead of array of tuples:
    {"purpose": "primary", "version": 2, "records":{"RecA":[
        "hello"
    ]}},
    # invalid field tuple:
    {"purpose": "primary", "version": 2, "records":{"RecA":[
        ["user", "fieldname", "fieldvalue", "ERROR"]
    ]}},
    # invalid field tuple:
    {"purpose": "primary", "version": 2, "records":{"RecA":[
        ["user", 1234, "fieldvalue", 1234]
    ]}},
    # invalid field tuple:
    {"purpose": "primary", "version": 2, "records":{"RecA":[
        ["user", "fieldname", "fieldvalue", 1234],
        ["user", "fieldname", "fieldvalue", "ERROR"]
    ]}},
    # invalid field tuple:
    {"purpose": "primary", "version": 2, "records":{"RecA":[
        ["user", "fieldname", "fieldvalue"],
    ]}},
    # invalid field tuple:
    {"purpose": "primary", "version": 2, "records":{"RecA":[
        ["user", "fieldname", "fieldvalue", 12356, "ERROR"],
    ]}},
       
]

@pytest.mark.parametrize("obj", invalid_json_objs)
def test_invalid_json(obj):
    obj_json = json.dumps(obj)
    with pytest.raises(jsonschema.exceptions.ValidationError):
        db = RawDatabase.from_json(obj_json)


def test_record_update():
    db = RawDatabase()
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('meta', 'path', 'Hello', 50)), must_create_record=True)
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'username', 'myName', 100)), cannot_create_record=False)
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'email', 'invalid@exmaple.com', 100)), cannot_create_record=True)
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'comment', 'HelloWorld', 100)), cannot_create_record=True)
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'password', 'ThisIsSecret', 100)), cannot_create_record=True)
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('meta', 'path', 'MyPath', 100)), cannot_create_record=True)
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'path', 'ThisUserFieldIsNamedPath', 100)), cannot_create_record=True)
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'username', 'myNewName', 150)), cannot_create_record=True)
    db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'username', 'myName', 200)), cannot_create_record=True)

    db.update(RawDatabaseUpdate('RecordB', FieldTuple('user', 'username', 'test', 200)))

    with pytest.raises(DatabaseException, match="called with must_created_record, but record already exists."):
        db.update(RawDatabaseUpdate('RecordB', FieldTuple('user', 'username', 'oops', 300)), must_create_record=True)

    with pytest.raises(DatabaseException, match="called with cannot_create_record, but record does not exist."):
        db.update(RawDatabaseUpdate('RecordC', FieldTuple('user', 'username', 'oops', 400)), cannot_create_record=True)

    with pytest.raises(DatabaseException, match="two identical field tuples with same mtime."):
        db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'username', 'myName', 100)))

    with pytest.raises(DatabaseException, match="two identical field tuples with same mtime."):
        db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'password', 'ThisIsSecret', 100)))

    with pytest.raises(DatabaseException, match="two different field tuples with same mtime."):
        db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'password', 'NewPassword', 100)))    

    with pytest.raises(DatabaseException, match="two different field tuples with same mtime."):
        db.update(RawDatabaseUpdate('RecordA', FieldTuple('user', 'email', 'NewEmail', 100)))    
