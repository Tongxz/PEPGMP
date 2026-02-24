"""
Examples package initialization.

This package provides example scripts demonstrating the usage of
PEPGMP's features without modifying sys.path. When examples are run
as modules (e.g., `python -m examples.domain_model_usage`),
the PYTHONPATH is automatically configured to include the project root.
"""

import sys
from pathlib import Path

# Add project root to Python path for all examples in this package
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
