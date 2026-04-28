"""Network loading utilities for the power system analysis tool."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

import pandapower as pp
import pandapower.networks as pn


SUPPORTED_CASES: dict[str, Callable[[], pp.pandapowerNet]] = {
    "IEEE 9 Bus": pn.case9,
    "IEEE 14 Bus": pn.case14,
    "IEEE 30 Bus": pn.case30,
}


def list_available_systems() -> list[str]:
    """Return available built-in test systems."""
    return list(SUPPORTED_CASES.keys())


def load_builtin_system(name: str) -> pp.pandapowerNet:
    """Load a built-in IEEE test system by name."""
    if name not in SUPPORTED_CASES:
        raise ValueError(f"Unsupported built-in system: {name}")
    return SUPPORTED_CASES[name]()


def load_uploaded_network(filename: str, file_bytes: bytes) -> pp.pandapowerNet:
    """Load a user-uploaded network from .json, .p, or .pickle files."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".json":
        return pp.from_json_string(file_bytes.decode("utf-8"))

    if suffix in {".p", ".pickle"}:
        with tempfile.NamedTemporaryFile(suffix=suffix) as temp:
            temp.write(file_bytes)
            temp.flush()
            return pp.from_pickle(temp.name)

    raise ValueError("Unsupported file type. Please upload a .json, .p, or .pickle network file.")
