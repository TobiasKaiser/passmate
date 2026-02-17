from pathlib import Path

from passmate.raw_db import FieldTuple, RawDatabaseUpdate
from passmate.session import SyncSummary


def test_sync_summary_messages_failure_and_success():
    summary = SyncSummary()
    summary.failure[Path("/tmp/remote-a.pmdb")] = "Passphrase incorrect."
    summary.success[Path("/tmp/remote-b.pmdb")] = [
        RawDatabaseUpdate(
            record_id="Rec1",
            field_tuple=FieldTuple("user", "username", "alice", 123),
        )
    ]

    assert list(summary.messages()) == [
        "Warning: Could not sync from remote-a.pmdb: Passphrase incorrect.",
        "remote-b.pmdb: 1 updates applied.",
    ]


def test_sync_summary_messages_skip_empty_success():
    summary = SyncSummary()
    summary.success[Path("/tmp/remote-a.pmdb")] = []

    assert list(summary.messages()) == []
