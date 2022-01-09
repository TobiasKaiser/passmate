class Session:
    """The Session object is used to access a primary database file for both
    read and write operations. The Session object also manages synchronization
    using synchronization copies and a shared folder.

    Any component that provides a user interface for Passmate should create
    one Session instance. Interactive interfaces should keep the Session open
    and close it only when the interactive session has ended."""
    
    def __init__(self, config):
        """config should be a Config object that can be read from the users's
        config.toml file."""
        self.config = config
