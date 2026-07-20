"""Stand-in for NVDA's ui module. init.py reads ui.message once at import
time via getattr(ui, 'message', None) - we provide a real one that records
calls, which is handy for tests that want to assert something was spoken."""

messages = []


def message(text):
    messages.append(text)
