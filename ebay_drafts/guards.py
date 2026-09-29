"""A local authorization latch, written BEFORE remote work, never from a response."""

from pathlib import Path

from . import AppError
from .files import check_path, read_bytes, write_bytes

GUARD_NAME = "submission-guard.json"
GUARD_BYTES = b'{"version":1,"requires_manual_review":true}\n'


def is_guarded(output: Path) -> bool:
    path = output / GUARD_NAME
    check_path(path)
    # Even an empty or damaged guard is a hold, never permission to upload.
    return path.exists()


def arm_guard(output: Path) -> None:
    if is_guarded(output):
        raise AppError("This item requires a Seller Hub review before another attempt.")
    write_bytes(output / GUARD_NAME, GUARD_BYTES)


def ensure_guard(output: Path) -> None:
    if not is_guarded(output):
        write_bytes(output / GUARD_NAME, GUARD_BYTES)


def release_guard(output: Path) -> None:
    path = output / GUARD_NAME
    if not is_guarded(output):
        raise AppError("This item has no local guard to release.")
    if read_bytes(path, 256) != GUARD_BYTES:
        raise AppError("The local guard is damaged or unrecognised. Review this file before retrying.")
    path.unlink()
