"""Small local-file helpers and a lock that Windows releases after a crash."""

from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import os
import re
import stat
import tempfile

from . import AppError
from .listing import read_json


def is_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        info = path.lstat()
        attrs = getattr(info, "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    # OneDrive placeholders may carry REPARSE_POINT without being links.
    tag = getattr(info, "st_reparse_tag", 0)
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT and tag in {0xA0000003, 0xA000000C})


def check_path(path: Path) -> None:
    if any(is_link(p) for p in (path, *path.parents)):
        raise AppError(f"Linked folders/files are not supported: {path.name}.")


def component(name: str) -> str:
    if (not isinstance(name, str) or not name or name.startswith(".") or len(name) > 255
            or name != name.rstrip(" .") or any(ord(c) < 32 or c in '<>:"/\\|?*' for c in name)
            or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", name, re.I)):
        raise AppError("Item folders must have ordinary Windows names, without nested paths.")
    return name


def read_bytes(path: Path, limit: int) -> bytes:
    check_path(path)
    if not path.is_file():
        raise AppError(f"Missing {path.name}.")
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise AppError(f"{path.name} is too large.")
    return content


def read_text(path: Path, limit: int) -> str:
    try:
        return read_bytes(path, limit).decode("utf-8-sig")
    except UnicodeError as error:
        raise AppError(f"Save {path.name} as UTF-8 in Notepad.") from error


def write_bytes(path: Path, content: bytes) -> None:
    check_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_text(path: Path, content: str) -> None:
    write_bytes(path, content.encode("utf-8"))


def workspace(root: Path, folder: str = "") -> Path:
    path = root / ".ebay-drafts"
    if folder:
        path /= sha256(folder.encode("utf-8")).hexdigest()[:24]
    check_path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_batch(root: Path, *, allow_legacy: bool = False) -> tuple[list[Path], dict[str, str]]:
    batch = read_json(read_text(root / "batch.json", 256_000))
    versions = {2, 3} if allow_legacy else {3}
    if set(batch) != {"version", "items", "skipped"} or type(batch["version"]) is not int or batch["version"] not in versions:
        raise AppError("Use a version 3 batch. Choose migration for a version 2 batch before uploading.")
    names, skipped = batch["items"], batch["skipped"]
    if not isinstance(names, list) or not isinstance(skipped, dict) or len(names) + len(skipped) > 100:
        raise AppError("A batch may contain up to 100 item folders. Ask ChatGPT to split larger batches.")
    all_names = [component(n) for n in names + list(skipped)]
    if len({n.casefold() for n in all_names}) != len(all_names):
        raise AppError("A folder appears more than once in batch.json.")
    actual = {p.name for p in root.iterdir() if p.is_dir()}
    if any(n not in actual for n in all_names):
        raise AppError("The overlay is not beside the original item folders. Extract it into the photo batch folder.")
    for name in all_names:
        check_path(root / name)
    if any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in skipped.values()):
        raise AppError("Every skipped item needs a short reason in batch.json.")
    return [root / n for n in names], skipped


@contextmanager
def batch_lock(root: Path):
    path = workspace(root) / "run.lock"
    check_path(path)
    with path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise AppError("This batch is already open in another run. Close that run first.") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
