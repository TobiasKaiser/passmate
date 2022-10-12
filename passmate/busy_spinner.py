import threading
import time
import sys
from contextlib import contextmanager

def print_spinner(event):
    delay=0.1
    while True:
        for x in ['-', '\\', '|', '/']:
            sys.stdout.write(f"\r{x}")
            sys.stdout.flush()
            if event.wait(timeout=delay):
                sys.stdout.write("\r \r")
                sys.stdout.flush()
                return

@contextmanager
def busy_spinner():
    event = threading.Event()
    t = threading.Thread(target=print_spinner, args=(event,))
    t.start()
    yield
    event.set()
    t.join()

if __name__=="__main__":
    with busy_spinner():
        time.sleep(3)