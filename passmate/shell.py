class Shell:
    """The Shell class provides a shell-like interface for accessing a
    passmate database."""
    def __init__(self, config):
        """config should be a Config object that can be read from the users's
        config.toml file."""
        self.config = config

    def run(self):
        """starts interactive shell-like session."""

        print("Hello, world!")
        print(self.config)
