# Passmate — A simple, secure password manager with multi-device synchronization

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Passmate on PyPI](https://img.shields.io/pypi/v/passmate.svg)](https://pypi.python.org/pypi/passmate)

Passmate is a command-line password manager that keeps your passwords encrypted and synchronized across multiple devices using a shared folder (like [Syncthing](https://syncthing.net/), Dropbox or any cloud storage).

## ✨ Features

* 🔒 **Strong Encryption**: All databases encrypted with scrypt. By using a single-file database, metadata leakage is minimzed.
* 🔄 **Automatic Sync**: Conflict-free synchronization across devices
* 💻 **Interactive Shell**: User-friendly command-line interface with tab completion
* 🌳 **Hierarchical Organization**: Organize passwords in folder-like paths
* 🎲 **Password Generator**: Built-in cryptographically strong password generator
* 🔍 **Smart Search**: Case-insensitive filtering across all records

## 📦 Installation

Using pip:

```bash
pip install passmate
```

From source:

```bash
git clone https://github.com/TobiasKaiser/passmate.git
cd passmate
pip3 install .
```

## 🚀 Quick Start

Simply run:

```bash
passmate
```

If this is your first time, passmate will automatically create a new encrypted database at `~/.local/share/passmate/local.pmdb` and prompt you to set a master passphrase.

For subsequent uses, just run `passmate` again and enter your passphrase.

## 📖 Usage

### Interactive Shell Commands

Once in the shell, you can use these commands:

**Managing Records**

```
new work/email/gmail          Create a new record
open work/email/gmail         Open an existing record
rename work/email/google      Rename current record
del                           Delete current record
close                         Close current record
```

**Editing Fields**

```
set username                  Set a field value
set password                  Set password field
gen password                  Generate secure password
unset password                Remove a field
show                          Display all fields
```

**Navigation & Organization**

```
ls                            List all records
ls gmail                      Search for records matching "gmail"
```

**Synchronization**

```
sync                          Sync with other devices
change_passphrase             Change master passphrase
```

**Other**

```
exit                          Exit passmate
```

### Example Session

```
passmate> new work/email/gmail
Record "work/email/gmail" created.

passmate:work/email/gmail> set username
Value: myemail@gmail.com

passmate:work/email/gmail> gen password
Template: Aaaaaaaaaaaaaa5
Settings: 15 characters including a-z, A-Z, 0-9
Generated password: xK9mPqR2nFwLyJa

passmate:work/email/gmail> show
username: myemail@gmail.com
password: xK9mPqR2nFwLyJa

passmate:work/email/gmail> close
passmate> exit
```

## 🔧 Configuration

Default configuration file: `~/.local/share/passmate/config.toml`

```toml
primary_db = "~/.local/share/passmate/local.pmdb"
shared_folder = "~/.local/share/passmate/sync/"
host_id = "laptop"
```

### Configuration Options

* **primary_db**: Path to your encrypted password database
* **shared_folder**: Path to folder for synchronization (e.g., Dropbox folder)
* **host_id**: Unique identifier for this device (defaults to hostname)

## 🔄 Multi-Device Synchronization

Passmate uses a conflict-free synchronization strategy based on timestamps (Last-Write-Wins strategy).

### Setup Instructions

1. **On Device 1:**

   ```bash
   passmate
   ```

2. **Configure shared folder** (edit `~/.local/share/passmate/config.toml`):

   ```toml
   shared_folder = "~/Dropbox/passmate/"
   host_id = "laptop"
   ```

3. **In the shell, run sync:**

   ```
   passmate> sync
   ```

4. **On Device 2:**

   Copy the configuration and set a different host_id:

   ```toml
   shared_folder = "~/Dropbox/passmate/"
   host_id = "desktop"
   ```

5. **On Device 2, start passmate:**

   ```bash
   passmate
   ```

   It will create a new database, then sync to pull data from Device 1.

**Master passphrase in multi-device setup:** For synchronization to work, you must use the same master passphrase on each device. If you change your master passphrase, you must do so on each device individually.

### How Sync Works

* Each device writes a sync copy to the shared folder.
* When you run `sync`, passmate reads all sync copies and merges changes.
* Conflicts are resolved automatically using modification timestamps.
* All changes are encrypted with your master passphrase.

## 🔐 Security

* All databases are encrypted using the [**scrypt**](https://www.tarsnap.com/scrypt.html) key derivation function (maxtime=1.0s, maxmem=16MB).
* Data is padded to 4KB increments to reduce metadata leakage.
* Password generation uses Python's `secrets` module (CSPRNG).

## 🔨 Development

There are some rudimentary tests:

```bash
pytest-3 .
```

To build the package's .whl and .tar.gz files, run:

```bash
python3 -m build
```

## 🔗 Links

* **Source Code**: https://github.com/TobiasKaiser/passmate
