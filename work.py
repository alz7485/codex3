"""Cooperative progress and cancellation shared by scans and file operations."""
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event


class Cancelled(Exception):
    pass


class WorkToken:
    def __init__(self):
        self.cancelled = Event()
        self.count = 0
        self.message = '準備中'
        self.journal = None

    def checkpoint(self, message='', rollback=False):
        if self.cancelled.is_set() and not rollback:
            raise Cancelled('キャンセルされました')
        self.count += 1
        self.message = message or self.message


current = ContextVar('folder_adjuster_work', default=None)


def checkpoint(message='', rollback=False):
    token = current.get()
    if token is not None:
        token.checkpoint(message, rollback)


@contextmanager
def working(token):
    handle = current.set(token)
    try:
        yield token
    finally:
        current.reset(handle)
