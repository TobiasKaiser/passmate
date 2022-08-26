import pytest
from passmate.session import SessionException, Record

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

        assert session.reload_counter == 1
        session.save()

    with start_session(tmp_path, init=False) as session:
        assert set(iter(session)) == set(["test1", "test2"])
        assert session.reload_counter == 1

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

        assert session.reload_counter == 1
        session.save()

    with start_session(tmp_path, init=False) as session:
        assert set(iter(session["MyRec"])) == set(["field1", "field2"])
        assert session["MyRec"]["field1"] == "value1"
        assert session["MyRec"]["field2"] == "NewValue"
        assert session.reload_counter == 1

def test_unbound_record(tmp_path): 
    r = Record()   
    with pytest.raises(SessionException, match="SessionError.UNBOUND_RECORD_ACCESS"):
        r["field1"] = "hello"
    with pytest.raises(SessionException, match="SessionError.UNBOUND_RECORD_ACCESS"):
        iter(r)
    with pytest.raises(SessionException, match="SessionError.UNBOUND_RECORD_ACCESS"):
        del r["fieldX"]
    with pytest.raises(SessionException, match="SessionError.UNBOUND_RECORD_ACCESS"):
        r["fieldX"]

def test_mtime_in_the_future(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session.current_time = 2000
        session["test1"] = Record()
        session["test1"]["field1"] = "hello"
        session["test1"]["field2"] = "world"
        session["delete_me"] = Record()
        session["rename_me"] = Record()

        session.current_time = 1000
        with pytest.raises(SessionException, match="SessionError.MTIME_IN_THE_FUTURE"):
            session["new_name"] = session["rename_me"]
        with pytest.raises(SessionException, match="SessionError.MTIME_IN_THE_FUTURE"):
            del session["delete_me"]
        with pytest.raises(SessionException, match="SessionError.MTIME_IN_THE_FUTURE"):
            session["test1"]["field1"] = "NewValue"
        with pytest.raises(SessionException, match="SessionError.MTIME_IN_THE_FUTURE"):
            del session["test1"]["field2"]