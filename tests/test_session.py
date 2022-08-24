import pytest
from passmate.session import SessionStarter, SessionException, SessionError, Record

from .start_session import start_session


def test_new_del_rename(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session["test1"] = Record()
        session["delete_me"] = Record()
        session["rename_me"] = Record()
        assert set(iter(session)) == set(["test1", "delete_me", "rename_me"])
        session["test2"] = session["rename_me"]
        assert set(iter(session)) == set(["test1", "delete_me", "test2"])
        
        del session["delete_me"]

        assert set(iter(session)) == set(["test1", "test2"])

        session.save()

    with start_session(tmp_path, init=False) as session:
        assert set(iter(session)) == set(["test1", "test2"])

def test_set_unset(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session["MyRec"] = Record()
        session["MyRec"]["field1"] = "value1"
        session["MyRec"]["field2"] = "value2"
        session["MyRec"]["field2"] = "NewValue"
        session["MyRec"]["field3"] = "delete_me"

        assert set(iter(session["MyRec"])) == set(["field1", "field2", "field3"])
        assert session["MyRec"]["field1"] == "value1"
        assert session["MyRec"]["field2"] == "NewValue"
        assert session["MyRec"]["field3"] == "delete_me"

        del session["MyRec"]["field3"]

        assert set(iter(session["MyRec"])) == set(["field1", "field2"])
        assert session["MyRec"]["field1"] == "value1"
        assert session["MyRec"]["field2"] == "NewValue"

        with pytest.raises(KeyError):
            session["MyRec"]["field3"]

        session.save()

    with start_session(tmp_path, init=False) as session:
        assert set(iter(session["MyRec"])) == set(["field1", "field2"])
        assert session["MyRec"]["field1"] == "value1"
        assert session["MyRec"]["field2"] == "NewValue"

def test_unbound_record(tmp_path):
    with start_session(tmp_path, init=True) as session:
        r = Record()
        with pytest.raises(SessionException, match="SessionError.UNBOUND_RECORD_ACCESS"):
            r["field1"] = "hello"
        with pytest.raises(SessionException, match="SessionError.UNBOUND_RECORD_ACCESS"):
            iter(r)
        with pytest.raises(SessionException, match="SessionError.UNBOUND_RECORD_ACCESS"):
            del r["fieldX"]
        with pytest.raises(SessionException, match="SessionError.UNBOUND_RECORD_ACCESS"):
            r["fieldX"]