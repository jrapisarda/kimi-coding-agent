"""Mock database migration runner."""
from __future__ import annotations

import time


def main() -> None:
    print("Starting Chopan database migrations...")
    time.sleep(0.1)
    print("Applying content schema migrations")
    time.sleep(0.1)
    print("Applying email schema migrations")
    time.sleep(0.1)
    print("Applying social schema migrations")
    time.sleep(0.1)
    print("Applying prospect schema migrations")
    time.sleep(0.1)
    print("Migrations complete")


if __name__ == "__main__":  # pragma: no cover
    main()
