"""
Kimi Agent - sprint one skeleton for the local-first multi-agent coding system.

This package exposes the CLI entrypoint and foundational orchestration,
persistence, and SDK abstractions delivered in sprint #1.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("kimi-agent")
except PackageNotFoundError:  # pragma: no cover - fallback for editable installs
    __version__ = "0.0.0"

__all__ = ["__version__"]
