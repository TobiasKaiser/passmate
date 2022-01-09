from dataclasses import dataclass
import json
import jsonschema

class DatabaseException(Exception):
    pass

@dataclass(frozen=True)
class FieldTuple:
    domain: str
    field_name: str
    field_value: str
    mtime: int

    def json(self):
        return (self.domain, self.field_name, self.field_value, self.mtime)

class RawRecord(list):
    pass

class RawDatabaseJSONEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return o.json()
        except AttributeError:
            return json.JSONEncoder.default(self, o)

class RawDatabase:

    json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Passmate database schema",
        "type": "object",
        "properties": {
            "purpose": {
                "description": "Distinguish between primary database and sync copy",
                "type": "string"
            }
        }, 
        "required": ["purpose", "records", "version"]
    }

    def __init__(self):
        self.is_sync_copy = False
        self.records = {}

    def json(self, purpose="primary"):
        if self.is_sync_copy:
            raise DatabaseException("json() called on sync copy")

        assert purpose in ("primary", "sync_copy")
        obj = {
            "version": 2,
            "purpose": purpose,
            "records": self.records
        }
        return RawDatabaseJSONEncoder().encode(obj)

    @classmethod
    def from_json(cls, json_str):
        obj = json.loads(json_str)

        jsonschema.validate(instance=obj, schema=cls.json_schema)

        db = RawDatabase()
        
        assert obj["version"] == 2
        # TODO: Replace this with JSON schema checking
        if obj["purpose"] == "sync_copy":
            db.is_sync_copy = True

        for record_id, field_tuples_json in obj["records"].items():
            record = RawRecord()
            for (domain, field_name, field_value, mtime) in field_tuples_json:
                field_tuple = FieldTuple(domain, field_name, field_value, mtime)
                record.append(field_tuple)
            assert not record_id in db.records
            db.records[record_id] = record

        return db

    def __repr__(self):
        return f"RawDatabase(is_sync_copy={self.is_sync_copy}, records={self.records})"