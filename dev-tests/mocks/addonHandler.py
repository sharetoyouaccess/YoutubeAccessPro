"""Stand-in for NVDA's addonHandler module. init.py calls
initTranslation() once at import time and never touches this module
again, so a no-op is sufficient."""


def initTranslation():
    pass
