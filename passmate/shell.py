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
from .busy_spinner import BusySpinner
from .generate import PasswordGenerator

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
    help_text = ""
    usage = ""

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

    def print_usage_error(self, details: str = "Invalid arguments.") -> None:
        print(f"{details} Usage: {self.usage}")

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

class CmdExit(Command):
    name = "exit"
    help_text = "Exit passmate."
    usage = "exit"

    def context_check(self):
        return True
    
    def handle(self, args):
        if len(args) > 0:
            self.print_usage_error("Command takes no arguments.")
            return

        return True # Exit

class CmdList(Command):
    name = "ls"
    help_text = "List records as a tree. Optionally filter by search term."
    usage = "ls [search_term]"

    def context_check(self):
        return True

    def handle(self, args):
        search_term = args
        print(self.session.tree.tree_str(search_term, TreeFormatterFancy()))

class CmdNew(Command):
    name = "new"
    help_text = "Create a new record and open it."
    usage = "new <path>"
    completion_handler = Command.completion_handler_path

    def context_check(self):
        return True

    def handle(self, args):
        path = args
        if len(path) == 0:
            self.print_usage_error("Missing record path.")
            return
        try:
            self.session[path] = Record()
        except SessionException as exc:
            if exc.error == SessionError.PATH_COLLISION:
                print(f"Record \"{path}\" already exists.")
                return
            raise
        self.shell.cur_path = path
        print(f"Record \"{path}\" created.")

class CmdRename(Command):
    name = "rename"
    help_text = "Rename current record."
    usage = "rename <new_path>"
    completion_handler = Command.completion_handler_path

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        old_path = self.shell.cur_path
        new_path = args
        if len(new_path) == 0:
            self.print_usage_error("Missing new record path.")
            return
        try:
            self.session[new_path] = self.session[old_path]
        except SessionException as exc:
            if exc.error == SessionError.PATH_COLLISION:
                print(f"Record \"{new_path}\" already exists.")
                return
            raise
        self.shell.cur_path = new_path
        print(f"Record \"{old_path}\" renamed to \"{new_path}\".")

class CmdOpen(Command):
    name = "open"
    is_default = True
    help_text = "Open an existing record."
    usage = "open <path>"
    completion_handler = Command.completion_handler_path

    def context_check(self):
        return self.shell.cur_path == None

    def handle(self, args):
        path = args
        if len(path) == 0:
            self.print_usage_error("Missing record path.")
            return
        if path in self.session:
            self.shell.cur_path = path
            self.shell.print_current_record()
        else:
            print(f"Record \"{path}\" not found.")

class CmdDelete(Command):
    name = "del"
    help_text = "Delete current record after confirmation."
    usage = "del"

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        if len(args)>0:
            self.print_usage_error("Command takes no arguments.")
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
    help_text = "Close current record."
    usage = "close"

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        if len(args) > 0:
            self.print_usage_error("Command takes no arguments.")
        else:
            self.shell.cur_path = None

class CmdShow(Command):
    name = "show"
    help_text = "Show all fields of current record."
    usage = "show"

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        if len(args) > 0:
            self.print_usage_error("Command takes no arguments.")
        else:
            self.shell.print_current_record()

class CmdSet(Command):
    name = "set"
    help_text = "Set a field value in current record."
    usage = "set <field_name>"
    completion_handler = Command.completion_handler_field_name

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        rec = self.session[self.shell.cur_path]

        field_name = args
        if len(field_name)==0:
            self.print_usage_error("Missing field name.")
            return
        
        try:
            old_value = rec[field_name]
        except KeyError:
            old_value = ""

        new_value = prompt("Value: ", default=old_value)

        rec[field_name] = new_value

class CmdGen(Command):
    name = "gen"
    help_text = "Generate a value from template and store it in a field."
    usage = "gen <field_name>"
    completion_handler = Command.completion_handler_field_name

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        rec = self.session[self.shell.cur_path]

        field_name = args
        if len(field_name)==0:
            self.print_usage_error("Missing field name.")
            return
        
        try:
            template_preset = rec[field_name]
        except KeyError:
            template_preset = self.session.config.template_preset

        template = prompt("Template: ", default=template_preset)

        g = PasswordGenerator.from_template(template)
        new_value = g.generate()

        print(f"Settings: {g.spec()}")
        print(f"Generated {field_name}: {new_value}")

        rec[field_name] = new_value

class CmdUnset(Command):
    name = "unset"
    help_text = "Delete a field from current record."
    usage = "unset <field_name>"
    completion_handler = Command.completion_handler_field_name

    def context_check(self):
        return self.shell.cur_path != None

    def handle(self, args):
        rec = self.session[self.shell.cur_path]

        field_name = args
        if len(field_name)==0:
            self.print_usage_error("Missing field name.")
            return

        try:
            del rec[field_name]
        except KeyError:
            print(f"Field \"{field_name}\" not found.")
        else:
            print(f"Field \"{field_name}\" deleted.")
    

class CmdChangePassphrase(Command):
    name = "change_passphrase"
    help_text = "Change the master passphrase."
    usage = "change_passphrase"

    def context_check(self):
        return self.shell.cur_path == None

    def handle(self, args):
        if len(args) > 0:
            self.print_usage_error("Command takes no arguments.")
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
    help_text = "Synchronize with other devices via shared folder."
    usage = "sync"

    def context_check(self):
        return self.shell.cur_path == None

    def handle(self, args):
        if len(args) > 0:
            self.print_usage_error("Command takes no arguments.")
            return

        with BusySpinner():
            summary = self.session.sync()
            self.session.save()

        for m in summary.messages():
            print(m)

class CmdHelp(Command):
    name = "help"
    help_text = "Show general help or details for one command."
    usage = "help [command]"

    def context_check(self):
        return True

    def completion_handler(self, text):
        for cmd in self.shell.all_commands:
            if cmd.name.startswith(text):
                yield Completion(cmd.name, start_position=-len(text), style='fg:ansired')

    def handle(self, args):
        cmd_name = args.strip()
        if not cmd_name:
            print("Passmate commands:")
            for cmd in self.shell.all_commands:
                available = "yes" if cmd.context_check() else "no"
                print(f"  {cmd.usage:<24} {cmd.help_text} (available now: {available})")
            print("Use: help <command>")
            return

        cmd = self.shell.command_by_name(cmd_name)
        if not cmd:
            print(f"Unknown command \"{cmd_name}\". Use: help")
            return

        print(f"{cmd.name}: {cmd.help_text}")
        print(f"Usage: {cmd.usage}")
        if not cmd.context_check():
            print("Currently unavailable in this context.")

class Shell:
    """
    The Shell class provides a shell-like interface for accessing a
    passmate database.
    """

    command_classes = [
        CmdHelp,
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
        CmdGen
    ]

    def __init__(self, session: Session):
        self.session = session
        self.cur_path = None

        self.all_commands = [cls(self) for cls in self.command_classes]

    def command_by_name(self, name: str) -> Command | None:
        for cmd in self.all_commands:
            if cmd.name == name:
                return cmd
        return None

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
                    print(f"{nothing:>{maxlen}}> {v}")

    def commands(self):
        """
        Generator for all currently available commands.
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
                    print("Unknown command. Use: help")
        except SessionException as exc:
            print(f"Error: {exc}")

    def run(self):
        """starts interactive shell-like session."""
        running = True
        session = PromptSession(key_bindings=self.key_bindings(), complete_style=CompleteStyle.READLINE_LIKE)

        while running:
            if self.session.save_required:
                with BusySpinner():
                    self.session.save()

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


def start_shell(config) -> Shell:
    """
    Args:
        config: Config object read from user's config.toml
        init: --init command line flag
    """

    sync_on_start = True

    config.shared_folder.mkdir(parents=True, exist_ok=True)

    init = False

    while True: # loop to allow repeated entry in case of a wrong passphrase.
        # Auto-initialize if database doesn't exist
        
        if not config.primary_db.exists():
            print("No database found. Creating a new one...")
            passphrase = read_set_passphrase(config.primary_db, initial=True)
            init = True  # Enable initialization for SessionStarter
        else:
            # Database exists, open normally
            passphrase = read_passphrase(config.primary_db, open=True)
        sp = BusySpinner()
        sp.start()
        try:
            with SessionStarter(config, passphrase, init) as session:
                if sync_on_start:
                    summary = session.sync()
                    for m in summary.messages():
                        print(m)
                sp.end()
                shell = Shell(session)
                shell.run()
        except SessionException as e:
            sp.end()
            if e.error == SessionError.WRONG_PASSPHRASE:
                print("Wrong passphrase, try again.")
                continue # Wrong passphrase -> re-run loop
            else:
                raise e
        else:
            break # Passphrase was presumably correct -> exit loop.
        finally:
            sp.end()
