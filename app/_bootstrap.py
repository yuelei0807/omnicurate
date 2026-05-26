"""Add project root to sys.path when Streamlit runs scripts under app/."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def setup() -> None:
    """Ensure imports like ``app.*`` and ``src.*`` resolve."""
    root = str(_PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
