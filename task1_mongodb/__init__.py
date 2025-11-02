"""task1_mongodb package initializer

This file makes the `task1_mongodb` directory a regular Python package so
imports like `import task1_mongodb` work reliably when running the API or
tests from the project root or other working directories.

Keep this file minimal; package-level exports can be added here later if
desired.
"""

__all__ = [
    "connect_db",
    "create_collections",
    "schema",
]
