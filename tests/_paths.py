"""Add plugin Python scripts to sys.path for imports."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "src" / "opnsense" / "scripts" / "NetDiscover"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
