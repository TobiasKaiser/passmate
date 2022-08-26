import getpass

def read_set_passphrase(filename, initial:bool):
    if initial:
        prompt1 = f'Passphrase to create {filename}: '
        prompt2 = f'Repeat passphrase to create {filename}: '
    else:
        prompt1 = f'Set new passphrase for {filename}: '
        prompt2 = f'Repeat new passphrase for {filename}: '

    passphrases_match = False
    while not passphrases_match:
        passphrase1 = getpass.getpass(prompt1)
        passphrase2 = getpass.getpass(prompt2)
        passphrases_match = (passphrase1 == passphrase2)
        if not passphrases_match:
            print("Passphrases do not match. Please try again.")
            print()
    return passphrase1

def read_passphrase(filename, open:bool):
    if open:
        prompt = f'Passphrase to open {filename}: '
    else:
        prompt = f'Enter current passphrase for {filename}: '
    return getpass.getpass(prompt)
