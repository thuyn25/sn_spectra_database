import numpy as np
from itertools import cycle
from shutil import get_terminal_size
from threading import Thread
from time import sleep


class Loader:
    def __init__(self, desc="Loading...", end="Done!", timeout=0.15):
        """
        A loader-like context manager
        Args:
            desc (str, optional): The loader's description. Defaults to "Loading...".
            end (str, optional): Final print. Defaults to "Done!".
            timeout (float, optional): Sleep time between prints. Defaults to 0.1.
        """
        self.desc = desc
        self.end = end
        self.timeout = timeout

        self._thread = Thread(target=self._animate, daemon=True)

        self.steps = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        self.done = False

    def start(self):
        self._thread.start()
        return self

    def _animate(self):
        while not self.done:
            cc = []
            for jj in range(0,4):
                i = np.random.randint(len(self.steps))
                c = self.steps[i]
                cc.append(c)
            print(f"\r{self.desc} \x1b[1;32;48m{cc[0]}{cc[1]}{cc[2]}{cc[3]}\x1b[0m", flush=True, end="")
            sleep(self.timeout)

    def __enter__(self):
        self.start()

    def stop(self):
        self.done = True
        cols = get_terminal_size((80, 20)).columns
        print("\r" + " " * cols, end="", flush=True)
        print(f"\r{self.end}", flush=True)

    def __exit__(self, exc_type, exc_value, tb):
        # handle exceptions with those variables ^
        self.stop()