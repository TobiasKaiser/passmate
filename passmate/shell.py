import getpass
import collections
from abc import ABC, ABCMeta, abstractmethod

from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.filters import completion_is_selected, has_completions
from prompt_toolkit.key_binding import KeyBindings

from .session import SessionStarter, Session, SessionError, SessionException

class PromptCompleter(Completer):
    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        #self.hier = PathHierarchy(shell.db)

    def get_completions(self, document, complete_event):
        # Complete only at end of line:
        if document.cursor_position!=len(document.text):
            return

        text = document.text

        # Complete command names
        if not " " in text:
            for cmd in self.shell.commands():
                if cmd.name.startswith(text):
                    yield Completion(cmd.name, start_position=-len(text), style='fg:ansired')

        
        # Call command handlers if applicable
        for cmd in self.shell.commands():
            if text.startswith(cmd.name+" "):
                yield from cmd.completion_handler(text[len(cmd.name)+1:])
                return

        # Call default handler else
        default_cmd = self.shell.default_command()
        if default_cmd:
            yield from default_cmd.completion_handler(text)

#    def handle_path(self, text):
#
#        start_idx=text.rfind("/")
#
#        var=text[start_idx+1:]
#        cur_dir = self.hier.root
#        if start_idx>=0:
#            for dirname in text.split("/")[:-1]:
#                try:
#                    cur_dir = cur_dir.subdirs[dirname]
#                except KeyError:
#                    return
#        for subdir in cur_dir.subdirs.keys():
#            subdir=subdir+"/"
#            if subdir.startswith(var):
#                yield Completion(subdir, start_position=-len(var), style='fg:ansiblue')
#        for record in cur_dir.records.keys():
#            if record.startswith(var):
#                yield Completion(record, start_position=-len(var))
#    
#    def handle_field_name(self, text):
#        for key in self.shell.cur_rec.fields.keys():
#            if key.startswith(text):
#                yield Completion(key, start_position=-len(text))

class Command(metaclass=ABCMeta):
    is_default = False

    def __init__(self, shell):
        self.shell = shell

    @abstractmethod
    def handle(self, args):
        """
        Return True to exit.
        """
        pass

    def completion_handler(self, text):
        return iter(())

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def context_check(self) -> bool:
        """
        Returns True if command is available in current context.
        """
        pass

class CmdSave(Command):
    name = "save"

    def context_check(self):
        return True
    
    def handle(self, args):
        if len(args)>0:
            print("?")
            return

        self.shell.session.save()


class CmdExit(Command):
    name = "exit"

    def context_check(self):
        return True
    
    def handle(self, args):
        if len(args)>0:
            print("?")
            return

        return True

class CmdList(Command):
    name = "ls"

    def context_check(self):
        return True

    def handle(self, args):
        s = self.shell.session
        print(s.records)

class Shell:
    """
    The Shell class provides a shell-like interface for accessing a
    passmate database.
    """

    command_classes = [
        CmdSave,
        CmdExit,
        CmdList,
    ]

    def __init__(self, session: Session):
        self.session = session
        self.cur_path = None

        self.all_commands = [cls(self) for cls in self.command_classes]

    def commands(self):
        """
        Genetor for all currently available commands.
        """
        for cmd in self.all_commands:
            if cmd.context_check():
                yield cmd

    def default_command(self) -> Command:
        default_cmd = None
        for cmd in self.commands():
            if cmd.is_default:
                assert (not default_cmd)
                default_cmd = cmd
        return default_cmd

    @property
    def cur_rec(self):
        return self.db.records[self.cur_path]

    def key_bindings(self):
        key_bindings = KeyBindings()

        @key_bindings.add("enter", filter=has_completions & ~completion_is_selected)
        def _(event):
            event.current_buffer.go_to_completion(0)
            event.current_buffer.complete_state = None

        @key_bindings.add("enter", filter=completion_is_selected)
        def _(event):
            event.current_buffer.complete_state = None
        return key_bindings

    def handle_cmd_named(self, text):
        text_s = text.split(" ", 1)
        cmd_name = text_s[0]
        try:
            args = text_s[1]
        except IndexError:
            args = ""

        for cmd in self.commands():
            if cmd.name == cmd_name:
                return cmd.handle(args)

        raise KeyError("Unknown command.")


    def handle_cmd(self, text):
        try:
            return self.handle_cmd_named(text)
        except KeyError:
            default_cmd = self.default_command()
            if default_cmd:
                return default_cmd.handle(text)
            else:
                print("?")

    def run(self):
        """starts interactive shell-like session."""
        running = True
        session = PromptSession(key_bindings=self.key_bindings(), complete_style=CompleteStyle.READLINE_LIKE)

        while running:
            my_completer=PromptCompleter(self)
            pathinfo=""
            if self.cur_path:
                pathinfo=":"+self.cur_path
            try:
                text = session.prompt(f'passmate{pathinfo}> ', completer=my_completer, complete_while_typing=True)
            except (EOFError, KeyboardInterrupt):
                # Exit on Ctrl+C or Ctrl+D.
                text = "exit"
            if self.handle_cmd(text):
                running=False


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

