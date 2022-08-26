import asyncio

from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys
import sys

class Confirmer:
    def __init__(self, question):
        self.question = question

    def keys_ready(self):
        for key_press in self.input.read_keys():
            if key_press.key in ('y', 'Y'):
                self.retval = True
                print('y')
            else:
                print('n')
            self.done.set()

    async def async_main(self):
        self.done = asyncio.Event()
        self.input = create_input()
        self.retval = False
        sys.stdout.write(self.question+' ')
        sys.stdout.flush()
        with self.input.raw_mode():
            with self.input.attach(self.keys_ready):
                await self.done.wait()
        return self.retval

def confirm_yes_no(question: str) -> bool:
    return asyncio.run(Confirmer(question).async_main())
