"""Stand-in for NVDA's logHandler module. Records every call instead of
writing to NVDA's real log file, so tests can assert on error/debug output
if they want to (e.g. verifying a failure path actually logs something,
rather than silently swallowing it - see round-10/11 audit findings)."""


class _FakeLog:
    def __init__(self):
        self.records = []

    def _record(self, level, msg):
        self.records.append((level, str(msg)))

    def debug(self, msg):
        self._record('debug', msg)

    def info(self, msg):
        self._record('info', msg)

    def warning(self, msg):
        self._record('warning', msg)

    def error(self, msg):
        self._record('error', msg)

    def exception(self, msg=''):
        self._record('exception', msg)


log = _FakeLog()
