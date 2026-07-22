"""Automatic selection of CinePlan's local or browser file transport."""

import os
import sys


_CLOUD_MARKERS = (
    "STREAMLIT_SHARING_MODE",
    "STREAMLIT_CLOUD",
    "STREAMLIT_RUNTIME_ENV",
)


def is_web_runtime(environ=None, platform=None):
    """Return True when native desktop dialogs are not available.

    Streamlit Community Cloud exposes cloud runtime markers and runs on Linux.
    CinePlan's supported native workflow is Windows, so non-Windows hosts use
    browser transport automatically as well.
    """
    environ = os.environ if environ is None else environ
    platform = sys.platform if platform is None else platform
    if platform != "win32":
        return True
    return any(str(environ.get(key, "")).strip() for key in _CLOUD_MARKERS)

