from dataclasses import dataclass
import json

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
    def __init__(self):
        self.purpose = "primary"
        self.records = {}

    def json(self):
        obj = {
            "version": 2,
            "purpose": self.purpose,
            "records": self.records
        }
        return RawDatabaseJSONEncoder().encode(obj)