"""Lightweight local checks for the project without external test frameworks.

This script validates import paths and key callable availability.
"""

from __future__ import annotations

import importlib


MODULES = [
    "src.network_loader",
    "src.power_flow",
    "src.contingency",
    "src.opf",
    "src.visualization",
    "src.metrics",
    "src.utils",
]


if __name__ == "__main__":
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        print(f"OK: {module_name} -> {module.__name__}")
