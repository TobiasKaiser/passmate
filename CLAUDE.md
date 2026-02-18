# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Passmate is a Python-based password manager with synchronization capabilities. It stores encrypted password databases and supports multi-device sync through a shared folder mechanism. The application provides an interactive shell interface built with prompt-toolkit.

## Development Commands

### Testing
```bash
python3 -m pytest                    # Run all tests
python3 -m pytest tests/test_pathtree.py  # Run specific test file
python3 -m pytest -v                 # Verbose output
```

### Running the Application
```bash
passmate                             # Open shell (auto-creates DB if needed)
passmate open                        # Same as above
passmate open --init                 # Force re-initialization (errors if DB exists)
passmate open <config.toml>          # Use custom config file
passmate migrate <in.pmdb> <out.pmdb>  # Migrate from v1 format
```

### Building and Installing
```bash
python3 -m build                     # Build distribution
python3 -m pip install -e .          # Install locally (editable)
```

## Architecture Overview

### Core Data Model

The application uses a three-layer data architecture:

1. **RawDatabase** (`raw_db.py`): Low-level storage layer
   - Stores records as ordered lists of `FieldTuple` objects
   - Each FieldTuple contains: domain, field_name, field_value, mtime
   - Maintains descending order by modification time (mtime)
   - Handles conflict-free merging using Last-Write-Wins (LWW) strategy

2. **Session** (`session.py`): Mid-level transaction layer
   - Provides user-facing API for database access
   - Manages file locking via `SessionStarter` context manager
   - Coordinates synchronization with remote databases
   - Maintains internal `_records` dict mapping paths to Record objects
   - Invalidates and reloads internal representation after merges

3. **Record** (`session.py`): High-level data abstraction
   - Dictionary-like interface for password record fields
   - Must be "bound" to a Session before use
   - Tracks modification times per field for conflict resolution
   - Supports metadata (path) and user data (password fields)

### State Management Pattern

Records and PathTree use an invalidation/lazy-reload pattern:
- After database merges, internal representations are invalidated
- Data is reloaded on next access via `reload_records_if_invalid()` and `reload_hierarchy_if_invalid()`
- Session tracks `reload_counter` to help detect when reloads occur

### Synchronization Architecture

Passmate implements a **conflict-free replicated data type (CRDT)** using Last-Write-Wins:

1. Primary database stored locally (default: `~/.local/share/passmate/local.pmdb`)
2. Sync copies written to shared folder (e.g., Dropbox/cloud storage)
3. Each device has a `host_id` (defaults to hostname)
4. Sync process (`Session.sync()`):
   - Reads all `.pmdb` files from shared_folder (except own host_id)
   - Merges updates from each sync copy into primary database
   - Uses mtime to resolve conflicts (newer always wins)
   - Returns SyncSummary with success/failure per sync copy

### Encryption

All databases encrypted with scrypt (`container.py`):
- Uses time-based key derivation (maxtime=1.0s)
- Padding to 4KB increments to reduce metadata leakage
- Atomic writes via temporary files and `shutil.move()`

### Interactive Shell

The Shell class (`shell.py`) provides a command-line interface:
- Context-sensitive commands (e.g., "set" only available when record is open)
- Tab completion for paths, field names, and commands
- Default commands execute without explicit command name (e.g., typing a path opens it)
- Auto-save triggers when `session.save_required` is True
- Commands are implemented as Command subclasses with `handle()` and optional `completion_handler()`

### Password Generation

`PasswordGenerator` (`generate.py`) uses cryptographically strong randomness:
- Template-based generation (e.g., "Aaaaaa5" → uppercase + lowercase + digit)
- Ensures at least one character from each requested type
- Uses `secrets` module for CSPRNG

## Key Implementation Details

### Path Handling

- Paths use forward slashes as separators (e.g., "work/email/gmail")
- PathTree (`pathtree.py`) builds hierarchical directory structure from flat path list
- Tree supports case-insensitive search filtering

### Time-Based Conflict Resolution

All updates include mtime (UNIX timestamp). When merging:
- Newer mtime always wins
- If mtimes equal for same field, raises DatabaseException
- Session uses `int(time.time())` for real time, `TimeTestSession` uses incrementing counter for tests

### Record Creation vs. Rename

Records track `creation_pending` state:
- New unbound Record: `creation_pending=True`, random record_id assigned
- Assigning to Session path: triggers `register_session_create()`, creates initial path field tuple
- Renaming existing record: updates path field tuple with new mtime, moves in `_records` dict

### Auto-Save Behavior

Shell main loop checks `session.save_required` before each prompt and saves if needed. Save operations are wrapped in `BusySpinner()` context manager for user feedback.

## Testing Patterns

Tests use `TimeTestSession` instead of `Session` to avoid time-based flakiness. Helper function `start_session()` in `tests/start_session.py` provides test session factory with temporary database files.

## Configuration

Default config location: `~/.local/share/passmate/config.toml`

Config fields (see `config.py`):
- `primary_db`: Path to main encrypted database file
- `shared_folder`: Path to folder for sync copies (e.g., Dropbox folder)
- `host_id`: Unique identifier for this device (defaults to hostname)
