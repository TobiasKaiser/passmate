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
                ["user", "password", "xyz", 5678]
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
    {},
    {"version": 2, "purpose": "blabla", "records": {}},
    {"version": 3, "purpose": "blabla", "records": {}},
]

@pytest.mark.parametrize("obj", invalid_json_objs)
def test_invalid_json(obj):
    obj_json = json.dumps(obj)
    with pytest.raises(jsonschema.exceptions.ValidationError):
        db = RawDatabase.from_json(obj_json)
