from passmate.raw_db import RawDatabase, RawRecord, FieldTuple
import json

def test_encode_json():
    db = RawDatabase()
    db.records["RecordA"] = RawRecord([
        FieldTuple("user", "email", "invalid@example.com", 123),
        FieldTuple("user", "password", "abcd", 124),
        FieldTuple("user", "password", "xyz", 5678),
    ])

    expected_obj = {
        "version": 2,
        "purpose": "primary",
        "records": {
            "RecordA":[
                ["user", "email", "invalid@example.com", 123],
                ["user", "password", "abcd", 124],
                ["user", "password", "xyz", 5678]
            ]
        }
    }
    generated_obj = json.loads(db.json())

    assert generated_obj == expected_obj