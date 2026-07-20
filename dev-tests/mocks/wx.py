"""Minimal stand-in for wxPython, just enough to import
globalPlugins/init.py and exercise its plain (non-GUI) functions on a
machine with no wx, no NVDA, and no Windows - which is what every test in
this suite needs, since none of them construct the actual UI classes.

Design: a generic `_Dummy` object answers any attribute access wx.py
doesn't explicitly define (via module-level __getattr__, PEP 562), so a
reference to some wx constant or class this suite happens not to use
directly (e.g. inside a key-handler method body that is never called here)
does not blow up the import. Only the handful of names that matter for
*importing* the module (Frame, Panel as base classes) or for making
request_playlist_items()'s background-thread callback testable
synchronously (CallAfter, CallLater) get real behavior.
"""

import threading


class _Dummy:
    """Stands in for any wx name this stub does not define for real.
    Usable as a class to instantiate, a callable, or an inert constant."""

    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return _Dummy()

    def __getattr__(self, name):
        return _Dummy()

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True

    def __hash__(self):
        return id(self)

    def __bool__(self):
        return False

    def __repr__(self):
        return '<wx._Dummy>'


def __getattr__(name):
    # PEP 562 module-level fallback - see module docstring.
    return _Dummy()


def CallAfter(fn, *args, **kwargs):
    """Real wx.CallAfter defers to the next GUI event loop iteration on the
    main thread. For tests we just call it immediately and synchronously,
    which is deterministic and lets tests assert on results right away."""
    fn(*args, **kwargs)


def CallLater(delay_ms, fn, *args, **kwargs):
    fn(*args, **kwargs)

    class _Timer:
        def Stop(self):
            pass

    return _Timer()


class Frame:
    def __init__(self, *a, **k):
        pass


class Panel:
    def __init__(self, *a, **k):
        pass


class Window:
    @staticmethod
    def FindFocus():
        return None
