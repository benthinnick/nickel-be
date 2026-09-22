from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def start_span(name: str, **attributes: str) -> Iterator[None]:
    yield
