# SPDX-FileCopyrightText: 2022 Tobias Kaiser <mail@tb-kaiser.de>
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import shutil
import scrypt
import os

# Scrypt parameters (explicit, static)
# This provides ~128MB memory cost and ~0.4s computation time
# See also: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
scrypt_logN = 17  # N = 2^17 = 131072
scrypt_r = 8
scrypt_p = 1

padding_increment = 4096

def pad_string(str_in):
    padded_len = (((len(str_in)-1)//padding_increment)+1) * padding_increment
    return str_in.ljust(padded_len)

def save_encrypted(filename: Path, passphrase: str, data_plain: str):
    filename_tmp = filename.with_suffix(filename.suffix+".tmp")

    data_plain_padded = pad_string(data_plain)

    data_scrypt = scrypt.encrypt(data_plain_padded, passphrase,
        logN=scrypt_logN, r=scrypt_r, p=scrypt_p)

    # Create pmdb file with mode 600, to prevent other users or group members
    # from accessing it:
    def opener(path, flags):
        return os.open(path, flags, 0o600)

    with open(filename_tmp, "wb", opener=opener) as f:
        f.write(data_scrypt)

    shutil.move(filename_tmp, filename)

def load_encrypted(filename: Path, passphrase: str) -> str:
    with open(filename, "rb") as f:
        data_scrypt = f.read()

    data_plain = scrypt.decrypt(data_scrypt, passphrase)

    return data_plain
