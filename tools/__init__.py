"""
Tools package initialization.

This package provides utility tools and visualization scripts without
modifying sys.path. When tools are run as modules (e.g., `python -m tools.visualize_regions`),
the PYTHONPATH is automatically configured to include the project root.
"""

import sys
from pathlib import Path

# Add project root to Python path for all tools in this package
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
