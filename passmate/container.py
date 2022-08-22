from pathlib import Path
import shutil
import scrypt

maxtime = 1.0
maxmem = 16*1024*1024
maxmemfrac = 0.5

padding_increment = 4096

def pad_string(str_in):
    padded_len = (((len(str_in)-1)//padding_increment)+1) * padding_increment
    return str_in.ljust(padded_len)

def save_encrypted(filename: Path, passphrase: str, data_plain: str):
    filename_tmp = filename.with_suffix(filename.suffix+".tmp")

    data_plain_padded = pad_string(data_plain)

    data_scrypt = scrypt.encrypt(data_plain_padded, passphrase,
        maxtime=maxtime, maxmem=maxmem, maxmemfrac=maxmemfrac)

    with open(filename_tmp, "wb") as f:
        f.write(data_scrypt)

    shutil.move(filename_tmp, filename)

def load_encrypted(filename: Path, passphrase: str) -> str:
    with open(filename, "rb") as f:
        data_scrypt = f.read()

    data_plain = scrypt.decrypt(data_scrypt, passphrase)

    return data_plain