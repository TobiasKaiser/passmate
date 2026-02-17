# SPDX-FileCopyrightText: 2022 Tobias Kaiser <mail@tb-kaiser.de>
# SPDX-License-Identifier: Apache-2.0

import pytest

from .start_session import start_session
from passmate.session import SessionException, Record
from passmate.raw_db import RawDatabase, RawDatabaseUpdate, FieldTuple
import copy

def sample_session_populate(session):
    session["record1"] = Record()
    session["path1/Record2"] = Record()
    session["path1/example3"] = Record()
    session["path2/x/y/z/abc/record4"] = Record()

sample_session_expected_tree = [
    "|",
    "+-> path1/",
    "| +-- Record2",
    "| +-- example3",
    "+-> path2/",
    "| +-> x/",
    "|   +-> y/",
    "|     +-> z/",
    "|       +-> abc/",
    "|         +-- record4",
    "+-- record1",
]

def test_pathtree(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)
        
        expected_tree = copy.copy(sample_session_expected_tree)

        assert session.tree.tree_str() == "\n".join(expected_tree)

def test_pathtree_search(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)
        
        expected_tree = [
            "|",
            "+-> path1/",
            "  +-- example3",
        ]

        assert session.tree.tree_str("example3") == "\n".join(expected_tree)
        
def test_pathtree_search_case_insensitive(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)
        
        expected_tree = [
            "|",
            "+-> path1/",
            "| +-- Record2",
            "+-> path2/",
            "| +-> x/",
            "|   +-> y/",
            "|     +-> z/",
            "|       +-> abc/",
            "|         +-- record4",
            "+-- record1",
        ]

        assert session.tree.tree_str("ReCord") == "\n".join(expected_tree)
        

def test_pathtree_search_path(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)
        
        expected_tree = [
            "|",
            "+-> path2/",
            "  +-> x/",
            "    +-> y/",
            "      +-> z/",
            "        +-> abc/",
            "          +-- record4",
        ]
        assert session.tree.tree_str("x/y/z") == "\n".join(expected_tree)
        

def test_pathtree_field_update(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)

        expected_tree = copy.copy(sample_session_expected_tree)

        assert session.tree.reload_counter == 0
        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 1

        # A field update should not cause a tree update:

        session["path1/Record2"]["my_field"] = "myValue"
        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 1

def test_pathtree_invalidate_new_record(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)

        expected_tree = copy.copy(sample_session_expected_tree)

        assert session.tree.reload_counter == 0
        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 1

        # Creation of a new record should trigger a tree update.

        session["path1/record5"] = Record()

        expected_tree.insert(4, "| +-- record5")

        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 2

def test_pathtree_invalidate_delete(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)

        expected_tree = copy.copy(sample_session_expected_tree)

        assert session.tree.reload_counter == 0
        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 1

        # Deletion of a record should trigger a tree update:

        del session["path2/x/y/z/abc/record4"]

        for line in [
                "+-> path2/",
                "| +-> x/",
                "|   +-> y/",
                "|     +-> z/",
                "|       +-> abc/",
                "|         +-- record4"]:
            expected_tree.remove(line)

        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 2

def test_pathtree_invalidate_rename(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)

        expected_tree = copy.copy(sample_session_expected_tree)

        assert session.tree.reload_counter == 0
        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 1
    
        # Renaming a record should trigger a tree update.

        session["renamed_record"] = session["path1/Record2"]

        expected_tree.remove("| +-- Record2",)
        expected_tree.append("+-- renamed_record")

        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 2

def test_pathtree_invalidate_merge(tmp_path):
    with start_session(tmp_path, init=True) as session:

        sample_session_populate(session)

        expected_tree = copy.copy(sample_session_expected_tree)

        assert session.tree.reload_counter == 0
        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 1
    

        # Operation 5: A merge should trigger a tree update.

        merge_in = RawDatabase()
        merge_in.update(RawDatabaseUpdate('RecordA', FieldTuple('meta', 'path', 'HelloWorld', 100)))
        session.merge(merge_in)
        expected_tree.append("+-- HelloWorld")

        assert session.tree.tree_str() == "\n".join(expected_tree)
        assert session.tree.reload_counter == 2
