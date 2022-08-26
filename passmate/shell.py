import collections
from abc import ABC, ABCMeta, abstractmethod

from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.filters import completion_is_selected, has_completions
from prompt_toolkit.key_binding import KeyBindings

from .session import SessionStarter, Session, Record, SessionError, SessionException
from .pathtree import TreeFormatterFancy
from .confirm_yes_no import confirm_yes_no

from .read_passphrase import read_set_passphrase, read_passphrase

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

    @property
    def session(self) -> Session:
        return self.shell.session

    def completion_handler_path(self, text):
        start_idx=text.rfind("/")

        var=text[start_idx+1:]
        cur_dir = self.session.tree.root
        if start_idx>=0:
            for dirname in text.split("/")[:-1]:
                try:
                    cur_dir = cur_dir.subdirs[dirname]
                except KeyError:
                    return
        for subdir in cur_dir.subdirs.keys():
            subdir=subdir+"/"
            if subdir.startswith(var):
                yield Completion(subdir, start_position=-len(var), style='fg:ansiblue')
        for record in cur_dir.records.keys():
            if record.startswith(var):
                yield Completion(record, start_position=-len(var))

    def completion_handler_field_name(self, text):
        rec = self.session[self.shell.cur_path]
        for key in iter(rec):
            if key.startswith(text):
                yield Completion(key, start_position=-len(text))

class CmdSave(Command):
    name = "save"

    def context_check(self):
        return True
    
    def handle(self, args):
        if len(args)>0:
            print("?")
            return

        if self.session.save():
            print("Changes saved.")
        else:
            print("No unsaved changes.")


class CmdExit(Command):
    name = "exit"

    def context_check(self):
        return True
    
    def handle(self, args):
        if not args in ["", "-f"]:
            print("?")
            return

        if self.session.save_required and args != "-f":
            print("Database has unsaved changes. Use 'save' to save changes or 'exit -f' to exit discarding changes.")
            return False
        else:
            return True

class CmdList(Command):
    name = "ls"

    def context_check(self):
        return True

    def handle(self, args):
        search_term = args
        print(self.session.tree.tree_str(search_term, TreeFormatterFancy()))

class CmdNew(Command):
    name = "new"
    completion_handler = Command.completion_handler_path

    def context_check(self):
        return True

    def handle(self, args):
        path = args
        self.session[path] = Record()
        self.shell.cur_path = path
        print(f"Record \"{path}\" created.")

class CmdRename(Command):
    name = "rename"
    completion_handler = Command.completion_handler_path

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        old_path = self.shell.cur_path
        new_path = args
        self.session[new_path] = self.session[old_path]
        self.shell.cur_path = new_path
        print(f"Record \"{old_path}\" renamed to \"{new_path}\".")

class CmdOpen(Command):
    name = "open"
    is_default = True
    completion_handler = Command.completion_handler_path

    def context_check(self):
        return self.shell.cur_path == None

    def handle(self, args):
        path = args
        if len(path) == 0:
            return
        if path in self.session:
            self.shell.cur_path = path
            self.shell.print_current_record()
        else:
            print(f"Record \"{path}\" not found.")

class CmdDelete(Command):
    name = "del"

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        if len(args)>0:
            print("?")
            return

        path = self.shell.cur_path

        if not confirm_yes_no(f"Do you want to delete record \"{path}\" (y/n)?"):
            return

        del self.session[path]
        self.shell.cur_path = None
        print(f"Record \"{path}\" deleted.")

class CmdClose(Command):
    name = "close"
    is_default = True

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        if len(args) > 0:
            print("?")
        else:
            self.shell.cur_path = None

class CmdShow(Command):
    name = "show"

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        if len(args) > 0:
            print("?")
        else:
            self.shell.print_current_record()

class CmdSet(Command):
    name = "set"
    completion_handler = Command.completion_handler_field_name

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        rec = self.session[self.shell.cur_path]

        field_name = args
        if len(field_name)==0:
            print("?")
            return
        
        try:
            old_value = rec[field_name]
        except KeyError:
            old_value = ""

        new_value = prompt("Value: ", default=old_value)

        rec[field_name] = new_value

class CmdUnset(Command):
    name = "unset"
    completion_handler = Command.completion_handler_field_name

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        rec = self.session[self.shell.cur_path]

        field_name = args
        if len(field_name)==0:
            print("?")
            return

        try:
            del rec[field_name]
            print(f"Field \"{field_name}\" deleted.")
        except KeyError:
            print(f"Field \"{field_name}\" not found.")

class CmdChangePassphrase(Command):
    name = "change_passphrase"

    def context_check(self):
        return self.shell.cur_path == None

    def handle(self, args):
        if len(args) > 0:
            print("?")
            return

        db_filename = self.session.config.primary_db

        if read_passphrase(db_filename, open=False) != self.session.passphrase:
            print("Wrong passphrase.")
            return

        new_passphrase = read_set_passphrase(db_filename, initial=False)
        self.session.set_passphrase(new_passphrase)
        print("Passphrase updated.")

class CmdSync(Command):
    name = "sync"

    def context_check(self):
        return self.shell.cur_path == None

    def handle(self, args):
        if len(args) > 0:
            print("?")
            return

        summary = self.session.sync()
        print(summary)

class Shell:
    """
    The Shell class provides a shell-like interface for accessing a
    passmate database.
    """

    command_classes = [
        CmdSave,
        CmdExit,
        CmdList,
        CmdNew,
        CmdRename,
        CmdOpen,
        CmdClose,
        CmdDelete,
        CmdShow,
        CmdSet,
        CmdUnset,
        CmdChangePassphrase,
        CmdSync,
    ]

    def __init__(self, session: Session):
        self.session = session
        self.cur_path = None

        self.all_commands = [cls(self) for cls in self.command_classes]

    def print_current_record(self):
        rec = self.session[self.cur_path]
        if len(rec)==0:
            print(f"Record \"{self.cur_path}\" is empty.")
        else:
            maxlen = max(map(len, iter(rec)))
            for field_name in rec:
                value = rec[field_name]
                value_multiline = value.split("\n")
                print(f"{field_name:>{maxlen}}: {value_multiline[0]}")
                for v in value_multiline[1:]:
                    nothing=""
                    print(f"{nothing:>{maxlen}}> {value_multiline}")

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
            try:
                return self.handle_cmd_named(text)
            except KeyError:
                default_cmd = self.default_command()
                if default_cmd:
                    return default_cmd.handle(text)
                else:
                    print("?")
        except SessionException as exc:
            print(f"Error: {exc}")

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
            passphrase = read_set_passphrase(config.primary_db, initial=True)
        else:
            if not config.primary_db.exists():
                print("Database not found. Pass --init to create new database.")
                return
            passphrase = read_passphrase(config.primary_db, open=True)
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

