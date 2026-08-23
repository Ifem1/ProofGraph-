"""Host-only compatibility shim for genlayer-test on Windows.

genlayer-test 0.29.2 replaces fd 0 with a temporary file and immediately
unlinks it. Windows refuses that unlink while fd 0 still owns the handle.
The shim is scoped to the test runner's loader module and only suppresses that
specific WinError 32; contract execution is unchanged.
"""

import os

_original_unlink = None

def pytest_configure():
    global _original_unlink
    try:
        import gltest.direct.loader as loader
    except ImportError:
        return

    original_unlink = os.unlink
    _original_unlink = original_unlink

    def unlink(path, *args, **kwargs):
        try:
            return original_unlink(path, *args, **kwargs)
        except PermissionError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 32:
                return None
            raise

    os.unlink = unlink

def pytest_unconfigure():
    if _original_unlink is not None:
        os.unlink = _original_unlink
