import pytest

from .start_session import start_session
from passmate.session import SessionException, Record

def test_pathtree(tmp_path):
    with start_session(tmp_path, init=True) as session:
        session.current_time = 2000
        session["record1"] = Record()
        session["path1/record2"] = Record()
        session["path1/record3"] = Record()
        session["path2/record4"] = Record()

        #print(session.tree)
        session.tree.print()