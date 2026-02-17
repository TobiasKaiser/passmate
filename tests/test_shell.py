# SPDX-FileCopyrightText: 2026 Tobias Kaiser <mail@tb-kaiser.de>
# SPDX-License-Identifier: Apache-2.0

"""
End-to-end tests for the interactive shell interface.

All tests use the full interactive loop via shell.run() with create_pipe_input()
to simulate realistic user typing and command sequences.
"""

import io
import sys
import string
import pytest
from contextlib import contextmanager
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.application import create_app_session

from passmate.shell import Shell
from passmate.session import Record
from .start_session import start_session


# Fixtures
@pytest.fixture
def session(tmp_path):
    with start_session(tmp_path, init=True) as sess:
        yield sess


# Helper functions
def run_shell(session, cmd_list: list[str]) -> tuple[str, Shell]:
    """Run shell with commands, return (output, shell). Exit is automatically appended."""
    shell = Shell(session)
    input_str = '\n'.join(cmd_list + ['exit']) + '\n'
    new_out = io.StringIO()
    old_out = sys.stdout
    try:
        sys.stdout = new_out
        with create_pipe_input() as pipe_input:
            pipe_input.send_text(input_str)
            with create_app_session(input=pipe_input, output=DummyOutput()):
                shell.run()
        return new_out.getvalue(), shell
    finally:
        sys.stdout = old_out


def populate_test_db(session):
    session["work/email"] = Record()
    session["work/email"]["username"] = "user@example.com"
    session["work/email"]["password"] = "work123"

    session["personal/banking/bank1"] = Record()
    session["personal/banking/bank2"] = Record()

    session["test_record"] = Record()


# Shell basics tests
# ------------------

def test_shell_initialization_and_exit(session):
    output, shell = run_shell(session, [])
    assert shell.cur_path is None
    assert shell.session is not None

# Navigation tests
# ----------------

def test_shell_ls_empty_db(session):
    output, _ = run_shell(session, ["ls"])
    assert output  # Should have some output


def test_shell_ls_with_records(session):
    populate_test_db(session)
    output, _ = run_shell(session, ["ls"])
    # Should contain some of the record paths
    assert "work" in output or "personal" in output or "test_record" in output


def test_shell_new_creates_record(session):
    assert "myrecord" not in session

    output, shell = run_shell(session, ["new myrecord"])

    assert "myrecord" in session
    assert shell.cur_path == "myrecord"  # Still open after creation
    assert "created" in output.lower()

def test_new_duplicate_name(session):
    output, shell = run_shell(session, ["new duplicate", "close", "new duplicate"])
    assert "already exists" in output.lower()
    assert set(iter(session)) == {"duplicate"}
    assert shell.cur_path is None


def test_shell_open_existing_record(session):
    populate_test_db(session)
    output, shell = run_shell(session, ["open work/email"])
    assert shell.cur_path == "work/email"


def test_shell_open_nonexistent_record(session):
    output, shell = run_shell(session, ["open nonexistent"])
    assert "not found" in output.lower()
    assert shell.cur_path is None  # Should not have changed


# Record operations tests
# -----------------------

def test_shell_new_and_close(session):
    output, shell = run_shell(session, ["new testrecord", "close"])
    assert "testrecord" in session
    assert shell.cur_path is None


def test_shell_new_show_close(session):
    output, shell = run_shell(session, ["new work/email", "show", "close"])
    assert "work/email" in session
    assert shell.cur_path is None
    assert "empty" in output.lower()  # New record should be empty


def test_shell_set_new_field(session):
    output, shell = run_shell(session, ["new test", "set password", "mypassword"])
    assert session["test"]["password"] == "mypassword"


def test_shell_set_existing_field(session):
    session["test"] = Record()
    session["test"]["password"] = "oldpass"

    output, shell = run_shell(session, ["open test", "set password", "\x15newpass"])
    assert session["test"]["password"] == "newpass"


def test_shell_show_after_set(session):
    output, shell = run_shell(session, ["new myaccount", "set password", "secret123", "show"])
    assert "password" in output.lower()
    assert "secret123" in output


def test_shell_multiple_fields(session):
    output, shell = run_shell(session, ["new account", "set username", "user@example.com", "set password", "mypassword"])
    assert session["account"]["username"] == "user@example.com"
    assert session["account"]["password"] == "mypassword"


# Workflow tests
# --------------

def test_shell_complete_workflow(session):
    output, shell = run_shell(session, ["new work/email", "set password", "mypassword", "show", "close"])

    assert "work/email" in session
    assert session["work/email"]["password"] == "mypassword"
    assert shell.cur_path is None  # Closed
    assert "password" in output.lower()


def test_shell_multiple_records(session):
    output, shell = run_shell(session, ["new record1", "set password", "pass1", "close", "new record2", "set password", "pass2", "close"])

    assert "record1" in session
    assert "record2" in session
    assert session["record1"]["password"] == "pass1"
    assert session["record2"]["password"] == "pass2"


def test_shell_ls_with_search(session):
    populate_test_db(session)
    output, _ = run_shell(session, ["ls work"])
    # Should filter to work-related records
    assert "work" in output


def test_shell_context_transitions(session):
    populate_test_db(session)
    output, shell = run_shell(session, ["open work/email", "close", "new another", "close"])
    assert shell.cur_path is None

def test_rename_duplicate_name(session):
    output, shell = run_shell(session, ["new a", "close", "new b", "close", "open a", "rename b"])
    assert "already exists" in output.lower()
    assert "a" in session
    assert "b" in session
    assert shell.cur_path == "a"


# Advanced tests
# --------------

def test_shell_error_recovery(session):
    output, _ = run_shell(session, ["invalidcommand", "open", "exit extra_args"])
    assert "not found" in output.lower()
    assert "Missing record path. Usage: open <path>" in output
    assert "Command takes no arguments. Usage: exit" in output

def test_shell_open_without_argument_shows_usage(session):
    output, shell = run_shell(session, ["open"])
    assert "Missing record path. Usage: open <path>" in output
    assert shell.cur_path is None

def test_shell_help_lists_commands(session):
    output, _ = run_shell(session, ["help"])
    assert "Passmate commands:" in output
    assert "help [command]" in output
    assert "new <path>" in output
    assert "sync" in output

def test_shell_help_for_specific_command(session):
    output, _ = run_shell(session, ["help rename"])
    assert "rename: Rename current record." in output
    assert "Usage: rename <new_path>" in output
    assert "Currently unavailable in this context." in output

def test_gen_uses_config_preset(tmp_path):
    with start_session(tmp_path, init=True, template_preset="A5") as session:
        output, _ = run_shell(session, ["new t", "gen pw", ""])
        generated = session["t"]["pw"]
        assert len(generated) == 2
        assert any(c in string.ascii_uppercase for c in generated)
        assert any(c in string.digits for c in generated)
