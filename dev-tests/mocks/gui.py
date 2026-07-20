"""Stand-in for NVDA's gui module. Only referenced inside __init__ methods
this test suite never calls (it never constructs MainWindow or
GlobalPlugin), so a generic fallback is enough."""


class _Dummy:
    def __getattr__(self, name):
        return _Dummy()

    def __call__(self, *a, **k):
        return _Dummy()


def __getattr__(name):
    return _Dummy()
