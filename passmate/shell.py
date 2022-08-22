from .session import SessionStarter, Session, SessionError, SessionException
import getpass


class Shell:
    """
    The Shell class provides a shell-like interface for accessing a
    passmate database.
    """
    def __init__(self, session: Session):
        self.session = session

    def run(self):
        """starts interactive shell-like session."""

        print(self.session)


def read_init_passphrase(filename):
    passphrases_match = False
    while not passphrases_match:
        passphrase1 = getpass.getpass(f'Passphrase to create {filename}: ')
        passphrase2 = getpass.getpass(f'Repeat passphrase to create {filename}: ')
        passphrases_match = (passphrase1 == passphrase2)
        if not passphrases_match:
            print("Passphrases do not match. Please try again.")
            print()
    return passphrase1

def read_passphrase(filename):
    return getpass.getpass(f'Passphrase to open {filename}: ')

def start_shell(config, init) -> Shell:
    """
    Args:
        config: Config object read from user's config.toml
        init: --init command line flag
    """

    while True: # loop to allow repeated entry in case of a wrong passphrase.
        if init:
            if config.primary_db.exists():
                print("--init specified with database already present.")
                return
            passphrase = read_init_passphrase(config.primary_db)
        else:
            if not config.primary_db.exists():
                print("Database not found. Pass --init to create new database.")
                return
            passphrase = read_passphrase(config.primary_db)
        try:
            with SessionStarter(config, passphrase, init) as session:
                shell = Shell(session)
                shell.run()
        except SessionException as e:
            if e.error == SessionError.WRONG_PASSPHRASE:
                print("Wrong passphrase, try again.")
                continue # Wrong passphrase -> re-run loop
            else:
                raise e
        else:
            break # Passphrase was presumably correct -> exit loop.

