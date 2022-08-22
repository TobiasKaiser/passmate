import pytest
import json
import jsonschema

from passmate.raw_db import RawDatabase, RawRecord, FieldTuple, DatabaseException


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
                ["user", "email", "invalid@example.com", 123],
                ["user", "password", "abcd", 124],
                ["user", "password", "xyz", 5678],
                ["user", "password", None, 5678]
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
