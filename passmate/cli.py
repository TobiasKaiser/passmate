import argparse
import toml
from pathlib import Path
from .config import Config
from .shell import start_shell
from .migrate_v1 import migrate

def init_config_if_missing(toml_fn):
    Path(toml_fn).parent.mkdir(parents=True, exist_ok=True)

    init_config = Config.default().dict()
    try:
        with open(toml_fn, "x") as f:
            toml.dump(init_config, f)
    except FileExistsError:
        pass

def load_config(toml_fn):
    with open(toml_fn, "r") as f:
        config_dict = toml.load(f)

    return Config(config_dict)

def main_open(args):
    init_config_if_missing(args.config_toml)
    config = load_config(args.config_toml)
    start_shell(config, args.init)

def main_migrate(args):
    migrate(args.pmdb_in, args.pmdb_out)

def default_config_fn():
    fn = Path.home() / ".local/share/passmate/config.toml"
    return str(fn)

def main():
    ap = argparse.ArgumentParser(prog="passmate")
    ap.set_defaults(action=main_open)
    ap.set_defaults(init=False)
    ap.set_defaults(config_toml=default_config_fn())

    subparsers = ap.add_subparsers(title="Commands")

    parser_open = subparsers.add_parser("open",
        help="Open passmate database for interactive access")
    parser_open.add_argument("config_toml", nargs="?",
        help="Configuration file",
        default=default_config_fn())
    parser_open.add_argument("--init", action="store_true")
    parser_open.set_defaults(action=main_open)
    
    parser_migrate = subparsers.add_parser("migrate",
        help="Migrate from old database format")
    parser_migrate.add_argument("pmdb_in", help="Input database file")
    parser_migrate.add_argument("pmdb_out", help="Output database file")
    parser_migrate.set_defaults(action=main_migrate)

    args = ap.parse_args()
    
    args.action(args)