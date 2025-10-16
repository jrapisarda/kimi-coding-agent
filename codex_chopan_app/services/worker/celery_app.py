"""Celery application bootstrap with graceful fallback."""
from __future__ import annotations

from typing import Any, Callable

try:  # pragma: no cover - exercised indirectly
    from celery import Celery  # type: ignore
except Exception:  # pragma: no cover - fallback path
    Celery = None  # type: ignore


class InMemoryCelery:
    """Very small stand-in that mimics task registration and delay."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tasks: dict[str, Callable[..., Any]] = {}

    def task(self, name: str | None = None, **_: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            task_name = name or func.__name__
            self.tasks[task_name] = func
            return func

        return decorator

    def send_task(self, name: str, *args: Any, **kwargs: Any) -> Any:
        func = self.tasks[name]
        return func(*args, **kwargs)


def create_celery(app_name: str) -> Any:
    if Celery is None:
        return InMemoryCelery(app_name)
    return Celery(app_name, broker="memory://", backend="cache+memory://")


app = create_celery("chopan-worker")
