"""CLI signal boundary: latch requests without raising inside native destructors."""

import signal
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from time import perf_counter
from types import FrameType


@contextmanager
def interruptible_clock() -> Iterator[Callable[[], float]]:
    if threading.current_thread() is not threading.main_thread():
        yield perf_counter
        return
    pending = False

    def request(signum: int, frame: FrameType | None) -> None:
        nonlocal pending
        pending = True

    def now() -> float:
        nonlocal pending
        if pending:
            pending = False
            raise KeyboardInterrupt
        return perf_counter()

    signals = [signal.SIGINT]
    if hasattr(signal, "SIGBREAK"):
        signals.append(signal.SIGBREAK)
    previous = {item: signal.getsignal(item) for item in signals}
    try:
        for item in signals:
            signal.signal(item, request)
        yield now
    finally:
        for item, handler in previous.items():
            signal.signal(item, handler)
