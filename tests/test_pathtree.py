import pytest

from .start_session import start_session
from passmate.session import SessionException, Record
from passmate.raw_db import RawDatabase, RawDatabaseUpdate, FieldTuple

def test_pathtree(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session.current_time = 2000
        session["record1"] = Record()
        session["path1/record2"] = Record()
        session["path1/record3"] = Record()
        session["path2/x/y/z/abc/record4"] = Record()

        expected_tree_str1 = "\n".join([
            "|",
            "+-> path1/",
            "| +-- record2",
            "| +-- record3",
            "+-> path2/",
            "| +-> x/",
            "|   +-> y/",
            "|     +-> z/",
            "|       +-> abc/",
            "|         +-- record4",
            "+-- record1",
        ])

        assert session.tree.reload_counter == 0
        assert session.tree.tree_str() == expected_tree_str1
        assert session.tree.reload_counter == 1

        # Operation 1: A field update should not cause a tree update.

        session["path1/record2"]["my_field"] = "myValue"
        assert session.tree.tree_str() == expected_tree_str1
        assert session.tree.reload_counter == 1

        # Operation 2: Creation of a new record should trigger a tree update.

        session["path1/record5"] = Record()

        expected_tree_str2 = "\n".join([
            "|",
            "+-> path1/",
            "| +-- record2",
            "| +-- record3",
            "| +-- record5",
            "+-> path2/",
            "| +-> x/",
            "|   +-> y/",
            "|     +-> z/",
            "|       +-> abc/",
            "|         +-- record4",
            "+-- record1",
        ])

        assert session.tree.tree_str() == expected_tree_str2
        assert session.tree.reload_counter == 2

        # Operation 3: Deletion of a record should trigger a tree update.

        del session["path2/x/y/z/abc/record4"]

        expected_tree_str3 = "\n".join([
            "|",
            "+-> path1/",
            "| +-- record2",
            "| +-- record3",
            "| +-- record5",
            "+-- record1",
        ])

        assert session.tree.tree_str() == expected_tree_str3
        assert session.tree.reload_counter == 3

        # Operation 4: Renaming a record should trigger a tree update.

        session["renamed_record"] = session["path1/record2"]

        expected_tree_str4 = "\n".join([
            "|",
            "+-> path1/",
            "| +-- record3",
            "| +-- record5",
            "+-- record1",
            "+-- renamed_record",
        ])

        assert session.tree.tree_str() == expected_tree_str4
        assert session.tree.reload_counter == 4

        # Operation 5: A merge should trigger a tree update.

        merge_in = RawDatabase()
        merge_in.update(RawDatabaseUpdate('RecordA', FieldTuple('meta', 'path', 'HelloWorld', 100)))
        session.merge(merge_in)

        expected_tree_str5 = "\n".join([
            "|",
            "+-> path1/",
            "| +-- record3",
            "| +-- record5",
            "+-- record1",
            "+-- renamed_record",
            "+-- HelloWorld",
        ])
        assert session.tree.tree_str() == expected_tree_str5
        assert session.tree.reload_counter == 5