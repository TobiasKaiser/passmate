import threading
import time
import sys
from contextlib import contextmanager

class BusySpinner:
    def print_spinner(self):
        delay=0.1
        while True:
            for x in ['-', '\\', '|', '/']:
                sys.stdout.write(f"\r{x}")
                sys.stdout.flush()
                if self.event.wait(timeout=delay):
                    sys.stdout.write("\r \r")
                    sys.stdout.flush()
                    return

    def __init__(self):
        self.event = None
        self.thread = None

    def start(self):
        assert not self.event
        self.event = threading.Event()
        self.thread = threading.Thread(target=self.print_spinner)
        self.thread.start()

    def end(self):
        if self.event:
            self.event.set()
            self.thread.join()
        self.event = None

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()

if __name__=="__main__":
    with BusySpinner():
        time.sleep(3)