from dataclasses import dataclass
import json
import jsonschema
import collections
import bisect

class DatabaseException(Exception):
    pass

RawDatabaseUpdate = collections.namedtuple(
    "RawDatabaseUpdate", ["record_id", "field_tuple"])

# Do not use functools.total_ordering here, as FieldTuple's native __eq__ from
# dataclass is needed to check for equality of all values, not just mtime.
@dataclass(frozen=True)
class FieldTuple:
    domain: str
    field_name: str
    field_value: str
    mtime: int

    def json(self):
        return (self.domain, self.field_name, self.field_value, self.mtime)

    def __int__(self):
        """For sorting by INVERSE mtime"""
        return -self.mtime

    # Apparently, only __lt__ is needed for bisect to work.
    def __lt__(self, other):
        return int(self) < int(other)


class RawRecord(list):

    def would_update(self, field_tuple: FieldTuple, ignore_existing: bool) -> int:
        """
        If field_tuple is not yet contained in the RawRecord, the correct
        insertion point (int) is returned. (The value could be 0.)

        If field_tuple is already present, None is returned.
        """

        # bisect here depends on the custom __lt__ of FieldTuple.
        # bisect's key paramater would be a cleaner solution.
        # I have decided against it though, because it requires Python 3.10.
        insertion_point = bisect.bisect_left(self, -field_tuple.mtime)

        # Check for duplicates:
        idx = insertion_point
        while idx < len(self) and self[idx].mtime == field_tuple.mtime:
            possible_duplicate = self[idx]
            # Duplicate mtime is only a problem when field tuple name and
            # domain match.
            same_field_name = (possible_duplicate.field_name == field_tuple.field_name)
            same_domain = (possible_duplicate.domain == field_tuple.domain)
            if same_field_name and same_domain:
                if possible_duplicate == field_tuple:
                    if ignore_existing:
                        return None # ignore, do not insert duplicate again.
                    else:
                        raise DatabaseException("Attempt to insert two identical field tuples with same mtime.")
                else:
                    assert possible_duplicate.field_value != field_tuple.field_value
                    raise DatabaseException("Attempt to insert two different field tuples with same mtime.")
            idx+=1

        return insertion_point

    def update(self, field_tuple: FieldTuple, ignore_existing: bool) -> bool:
        """
        Maintains descending ordering by mtime.

        Returns:
            True when field_tuple was inserted, False if it was not inserted
            (only possible when ignore_existing was set to True).
        """

        insertion_point = self.would_update(field_tuple, ignore_existing)

        # FieldTuple is inserted unless we had a duplicate that raised a
        # DatabaseException or returned None as insertion point.

        if insertion_point == None:
            return False
        else:
            self.insert(insertion_point, field_tuple)
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

    def would_update(self, u:RawDatabaseUpdate, ignore_existing=False):
        try:
            rec = self.records[u.record_id]
        except KeyError:
            return True
        else:
            insertion_point = self.records[u.record_id].would_update(u.field_tuple, ignore_existing)
            return insertion_point != None

    def to_updates(self):
        """
        Generator of RawDatabaseUpdate objects, which can be used to merge
        the contents of this database into another database (see merge method).
        """
        for record_id, field_tuples in self.records.items():
            for field_tuple in field_tuples:
                yield RawDatabaseUpdate(record_id, field_tuple)

    def merge(self, other) -> list[RawDatabaseUpdate]:
        """
        Returns a list of the RawDatabaseUpdates, which must be applied to the
        RawDatabase in order to merge the RawDatabase other into the RawDatabase
        on which this method was called.

        Args:
            other: another RawDatabase object.

        Returns:
            List of RawDatabaseUpdates.
        """
        return list(filter(
            lambda u: self.would_update(u, ignore_existing=True),
            other.to_updates()
            ))