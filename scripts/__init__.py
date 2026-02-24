"""
Scripts package initialization.

This package provides a standard way to run utility scripts without
modifying sys.path. When scripts are run as modules (e.g., `python -m scripts.init_database`),
the PYTHONPATH is automatically configured to include the project root.
"""

import sys
from pathlib import Path

# Add project root to Python path for all scripts in this package
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
