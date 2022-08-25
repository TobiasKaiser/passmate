from dataclasses import dataclass
import json
import jsonschema
import collections
import bisect

class DatabaseException(Exception):
    pass

RawDatabaseUpdate = collections.namedtuple(
    "RawDatabaseUpdate", ["record_id", "field_tuple"])


@dataclass(frozen=True)
class FieldTuple:
    domain: str
    field_name: str
    field_value: str
    mtime: int

    def json(self):
        return (self.domain, self.field_name, self.field_value, self.mtime)

class RawRecord(list):
    def update(self, field_tuple: FieldTuple, ignore_existing: bool) -> bool:
        """
        Maintains descending ordering by mtime.

        Returns:
            True when field_tuple was inserted, False if it was not inserted
            (only possible when ignore_existing was set to True).
        """
        idx = bisect.bisect_left(self, -field_tuple.mtime, key=lambda ft: -ft.mtime)
        try:
            possible_duplicate = self[idx]
        except IndexError:
            pass
        else:
            if possible_duplicate.mtime == field_tuple.mtime:
                if possible_duplicate == field_tuple:
                    if ignore_existing:
                        return False # ignore, do not insert duplicate again.
                    else:
                        raise DatabaseException("Attempt to insert two identical field tuples with same mtime.")
                else:
                    raise DatabaseException("Attempt to insert two different field tuples with same mtime.")
        
        self.insert(idx, field_tuple)
        return True

class RawDatabaseJSONEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return o.json()
        except AttributeError:
            return json.JSONEncoder.default(self, o)

class RawDatabase:

    json_schema = {
        "$schema": "http://json-schema.org/draft-07/schema",
        "title": "Passmate database schema",
        "type": "object",
        "properties": {
            "version":{
                "description":"Passmate database version",
                "const":2
            },
            "purpose": {
                "description": "Distinguish between primary database and sync copy",
                "enum":["primary", "sync_copy"]
            },
            "records": {
                "type": "object",
                "patternProperties": {
                    "": {
                        "type": "array",
                        "description": "Array of field tuples",
                        "items": {
                            "type": "array",
                            "description": "Field tuple",
                            "items": [
                                {
                                    "type": "string",
                                    "description": "Field domain",
                                    "enum":["user", "meta"]
                                },
                                {
                                    "type": "string",
                                    "description": "Field name"
                                },
                                {
                                    "type": ["string", "null"],
                                    "description": "Field value"
                                },
                                {
                                    "type": "integer",
                                    "description": "Modification time"
                                },
                            ],
                            "additionalItems":False,
                            "minItems":4,
                            "maxItems":4
                        }
                    }
                }
            }
        }, 
        "required": ["purpose", "records", "version"],
        "additionalProperties": False
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
        
        if obj["purpose"] == "sync_copy":
            db.is_sync_copy = True

        for record_id, field_tuples_json in obj["records"].items():
            for idx, (domain, field_name, field_value, mtime) in enumerate(field_tuples_json):
                field_tuple = FieldTuple(domain, field_name, field_value, mtime)
                u = RawDatabaseUpdate(record_id, field_tuple)
                first_tuple = (idx == 0)
                db.update(u, must_create_record=first_tuple, cannot_create_record=(not first_tuple))
                
        return db

    def __repr__(self):
        return f"RawDatabase(is_sync_copy={self.is_sync_copy}, records={self.records})"

    def update(self, u:RawDatabaseUpdate, must_create_record=False,
            cannot_create_record=False, ignore_existing=False):
        """
        Maintains ordered list by using RawRecord.update

        Args:
            must_create_record: For assertion during DB loading
            cannot_create_record: For assertion during DB loading
            ignore_existing: Set to True when merging updates from another DB.
        """
        if u.record_id in self.records:
            if must_create_record:
                raise DatabaseException("update() called with must_created_record, but record already exists.")
        else:
            if cannot_create_record:
                raise DatabaseException("update() called with cannot_create_record, but record does not exist.")
            self.records[u.record_id] = RawRecord()

        return self.records[u.record_id].update(u.field_tuple, ignore_existing=ignore_existing)

    def to_updates(self):
        """
        Generator of RawDatabaseUpdate objects, which can be used to merge
        the contents of this database into another database (see merge method).
        """
        for record_id, field_tuples in self.records.items():
            for field_tuple in field_tuples:
                yield RawDatabaseUpdate(record_id, field_tuple)

    def merge(self, other):
        """
        Merges the RawDatabase other in the RawDatabase on which the method was
        called.

        Returns:
            A list of all applied RawDatabaseUpdates.
        """
        applied_updates = []
        for u in other.to_updates():
            if self.update(u, ignore_existing=True):
                applied_updates.append(u)
        return applied_updates