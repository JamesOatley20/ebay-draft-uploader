"""Bounded, restartable cleanup. Only explicitly supplied batch roots are inspected."""

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import json
import os
import re

from . import AppError
from .feed import is_preparation_csv
from .files import check_path, component, load_batch, read_bytes, write_bytes
from .guards import GUARD_BYTES, GUARD_NAME, ensure_guard
from .listing import Listing, read_json
from .notes import STATUS_MARKER, PREPARATION_MARKER, authored_prefix, section_start

MARKER = "migration-in-progress"
HASH_NAME = re.compile(r"[0-9a-f]{24}")
TEMP_NAME = re.compile(r"\.tmp-[a-z0-9_]{8}")
SUSPICIOUS = re.compile(
    rb'(?i)"(?:access_token|refresh_token|task_id|taskId|imageUrl|expirationDate|previous_tasks)"\s*:'
    rb'|authorization\s*:\s*bearer\s+|https://[^\s/"]*\.ebayimg\.com/'
)


def app_storage() -> Path | None:
    value = os.environ.get("LOCALAPPDATA")
    return Path(value).absolute() / "eBayDrafts" if value else None


@dataclass
class MigrationPlan:
    roots: tuple[Path, ...]
    storage: Path | None
    deletes: set[Path] = field(default_factory=set)
    rewrites: dict[Path, bytes] = field(default_factory=dict, repr=False)
    upgrades: dict[Path, bytes] = field(default_factory=dict, repr=False)
    guards: set[Path] = field(default_factory=set)
    markers: set[Path] = field(default_factory=set)
    issues: list[tuple[Path, str]] = field(default_factory=list)
    snapshots: dict[Path, tuple] = field(default_factory=dict, repr=False)

    @property
    def needed(self) -> bool:
        return bool(self.deletes or self.rewrites or self.upgrades or self.guards or self.markers or self.issues)

    def describe(self) -> list[str]:
        rows = []
        for label, paths in (("Delete old generated file", self.deletes),
                             ("Preserve local content / remove app status", self.rewrites),
                             ("Upgrade batch version", self.upgrades),
                             ("Keep local guard", self.guards),
                             ("Finish interrupted migration", self.markers)):
            rows += [f"{label}: {p}" for p in sorted(paths)]
        rows += [f"REVIEW: {p} — {reason}" for p, reason in self.issues]
        return rows


def _snapshot(path: Path) -> tuple:
    check_path(path)
    if not path.exists():
        return ("missing",)
    if path.is_dir():
        entries = list(path.iterdir())
        if len(entries) > 10000:
            raise AppError("A storage directory is too large for automatic migration.")
        return ("directory", tuple(sorted(p.name for p in entries)))
    if not path.is_file() or path.stat().st_size > 12 * 1024 * 1024:
        raise AppError("A generated file is unrecognised or too large for automatic migration.")
    if path.name == "run.lock" and path.parent.name == ".ebay-drafts":
        # Windows byte locks also forbid a second handle in this same process
        # from reading the locked byte. This fixed-size file contains no API data.
        return ("lock", path.stat().st_size)
    return ("file", sha256(read_bytes(path, 12 * 1024 * 1024)).hexdigest())


def _watch(plan: MigrationPlan, path: Path) -> None:
    plan.snapshots[path] = _snapshot(path)


def _inside(plan: MigrationPlan, path: Path) -> None:
    check_path(path)
    resolved = path.resolve()
    allowed = (*plan.roots, *((plan.storage,) if plan.storage else ()))
    if not any(resolved.is_relative_to(root) for root in allowed):
        raise AppError("Migration refused a path outside the selected storage.")
    if path.exists() and not path.is_file():
        raise AppError("Migration only replaces or deletes recognised files.")


def _check_authored(plan: MigrationPlan, path: Path, content: bytes) -> None:
    if SUSPICIOUS.search(content):
        plan.issues.append((path, "Possible account/API data outside the app-owned section; review locally. Contents were not printed."))


def _rescue(plan: MigrationPlan, state_path: Path, folder: Path | None) -> None:
    try:
        state = read_json(read_bytes(state_path, 256_000).decode("utf-8-sig"))
        if state.get("version") != 2:
            raise ValueError()
        for key, filename, fallback in (("listing", "listing.json", "recovered-listing.json"),
                                        ("seller_notes", "input.txt", "recovered-input.txt")):
            if key not in state:
                continue
            destination = folder / filename if folder else state_path.parent / fallback
            _watch(plan, destination)
            if destination.exists():
                continue
            if key == "listing":
                content = (json.dumps(Listing.parse(state[key]).as_dict(), indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            else:
                if not isinstance(state[key], str) or len(state[key].encode("utf-8")) > 32_000:
                    raise ValueError()
                content = state[key].encode("utf-8")
            _check_authored(plan, destination, content)
            plan.rewrites[destination] = content
    except (AppError, UnicodeError, ValueError, TypeError, KeyError):
        plan.issues.append((state_path, "Cannot safely identify local preparation snapshots in this old state; review before deleting."))


def inspect_migration(roots: list[Path] | tuple[Path, ...], storage: Path | None = None) -> MigrationPlan:
    resolved = []
    for root in roots:
        check_path(root)
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise AppError("Migration needs an existing batch directory.")
        if root not in resolved:
            resolved.append(root)
    if storage is not None:
        check_path(storage)
        storage = storage.resolve()
    plan = MigrationPlan(tuple(resolved), storage)
    if storage:
        _watch(plan, storage)
        if storage.exists():
            for path in storage.iterdir():
                _watch(plan, path)
                if path.name == MARKER and path.is_file():
                    plan.markers.add(path)
                elif path.is_file() and (path.name == "sign-in.bin" or TEMP_NAME.fullmatch(path.name)):
                    plan.deletes.add(path)
                elif path.name != "tool-path.txt" or not path.is_file():
                    plan.issues.append((path, "Unrecognised app-storage entry; it will not be deleted automatically."))
    for root in plan.roots:
        _watch(plan, root)
        load_batch(root, allow_legacy=True)
        manifest = root / "batch.json"
        _watch(plan, manifest)
        batch = read_json(read_bytes(manifest, 256_000).decode("utf-8-sig"))
        legacy = batch["version"] == 2
        if legacy:
            upgraded = {"version": 3, "items": batch["items"], "skipped": batch["skipped"]}
            plan.upgrades[manifest] = (json.dumps(upgraded, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        for path in root.iterdir():
            if path.name.startswith(".tmp-"):
                _watch(plan, path)
                try:
                    temporary_batch = read_json(read_bytes(path, 256_000).decode("utf-8-sig"))
                    recognised = (TEMP_NAME.fullmatch(path.name) and set(temporary_batch) == {"version", "items", "skipped"}
                                  and temporary_batch["version"] in {2, 3})
                except (AppError, UnicodeError, ValueError):
                    recognised = False
                if recognised:
                    plan.deletes.add(path)
                else:
                    plan.issues.append((path, "Unrecognised root temporary file; review it locally."))
        # Include no-longer-selected immediate item folders, without recursive scanning.
        folders = {}
        for folder in root.iterdir():
            if folder.name.startswith(".") or not folder.is_dir():
                continue
            check_path(folder)
            component(folder.name)
            folders[sha256(folder.name.encode("utf-8")).hexdigest()[:24]] = folder
            _watch(plan, folder)
            for name in ("listing.json", "input.txt", "output.txt"):
                path = folder / name
                _watch(plan, path)
                if not path.exists():
                    continue
                content = read_bytes(path, 256_000)
                prefix = authored_prefix(content) if name == "output.txt" else content
                _check_authored(plan, path, prefix)
                if name == "output.txt" and section_start(content, STATUS_MARKER) is not None:
                    plan.rewrites[path] = prefix
                    plan.guards.add(root / ".ebay-drafts" / sha256(folder.name.encode()).hexdigest()[:24])
            for path in folder.iterdir():
                if not path.name.startswith(".tmp-"):
                    continue
                _watch(plan, path)
                content = read_bytes(path, 256_000)
                if TEMP_NAME.fullmatch(path.name) and any(section_start(content, marker) is not None for marker in (STATUS_MARKER, PREPARATION_MARKER)):
                    plan.deletes.add(path)
                    plan.guards.add(root / ".ebay-drafts" / sha256(folder.name.encode()).hexdigest()[:24])
                else:
                    plan.issues.append((path, "Cannot establish ownership of this temporary file; review it locally."))
        ws = root / ".ebay-drafts"
        _watch(plan, ws)
        if not ws.exists():
            continue
        for path in ws.iterdir():
            _watch(plan, path)
            if path.is_file():
                if path.name == MARKER:
                    plan.markers.add(path)
                elif path.name == "run.lock":
                    if path.stat().st_size not in (0, 1):
                        plan.issues.append((path, "Unrecognised lock contents."))
                elif path.name == "preview.html":
                    content = read_bytes(path, 12 * 1024 * 1024)
                    if legacy or b"<title>eBay draft preparation</title>" not in content or SUSPICIOUS.search(content):
                        plan.deletes.add(path)
                elif TEMP_NAME.fullmatch(path.name):
                    plan.deletes.add(path)
                    plan.guards.update(ws / key for key in folders)
                else:
                    plan.issues.append((path, "Unrecognised generated file; review before migration."))
                continue
            if not path.is_dir() or not HASH_NAME.fullmatch(path.name):
                plan.issues.append((path, "Unrecognised storage directory; no recursive cleanup will be attempted."))
                continue
            for artifact in path.iterdir():
                _watch(plan, artifact)
                if artifact.name == "photos" and artifact.is_dir():
                    for photo in artifact.iterdir():
                        _watch(plan, photo)
                        if not photo.is_file() or not (re.fullmatch(r"(?:0[1-9]|1[0-2])\.jpg", photo.name) or TEMP_NAME.fullmatch(photo.name)):
                            plan.issues.append((photo, "Unrecognised photo-cache entry."))
                        elif TEMP_NAME.fullmatch(photo.name):
                            plan.deletes.add(photo)
                    continue
                if not artifact.is_file():
                    plan.issues.append((artifact, "Unrecognised generated directory."))
                elif artifact.name in {"state.json", "result.bin"} or TEMP_NAME.fullmatch(artifact.name):
                    plan.deletes.add(artifact)
                    plan.guards.add(path)
                    if artifact.name == "state.json":
                        _rescue(plan, artifact, folders.get(path.name))
                elif artifact.name == "draft.csv":
                    if legacy or not is_preparation_csv(read_bytes(artifact, 256_000)):
                        plan.deletes.add(artifact)
                        plan.guards.add(path)
                elif artifact.name == GUARD_NAME:
                    if read_bytes(artifact, 256) != GUARD_BYTES:
                        plan.issues.append((artifact, "Unrecognised local guard; review before releasing."))
                elif artifact.name in {"recovered-listing.json", "recovered-input.txt"}:
                    _check_authored(plan, artifact, read_bytes(artifact, 256_000))
                else:
                    plan.issues.append((artifact, "Unrecognised generated file; it will not be deleted automatically."))
    return plan


def require_clean(root: Path, storage: Path | None) -> None:
    plan = inspect_migration([root], storage)
    if plan.needed:
        raise AppError("Legacy or unrecognised storage needs review. Choose migration first; no eBay request was made.")


def apply_migration(plan: MigrationPlan) -> None:
    """Caller holds batch locks and has shown describe() before explicit approval."""
    if plan.issues:
        raise AppError("Resolve the listed migration review items first. Nothing was deleted.")
    for path, snapshot in plan.snapshots.items():
        if _snapshot(path) != snapshot:
            raise AppError("Files changed since migration review. Inspect the cleanup plan again.")
    if not plan.needed:
        return
    markers = set(plan.markers)
    for root in plan.roots:
        markers.add(root / ".ebay-drafts" / MARKER)
    if plan.storage:
        markers.add(plan.storage / MARKER)
    # Validate every target before making the first change, then recheck at use.
    for path in (plan.deletes | set(plan.rewrites) | set(plan.upgrades) | markers
                 | {output / GUARD_NAME for output in plan.guards}):
        _inside(plan, path)
    for marker in markers:
        _inside(plan, marker)
        write_bytes(marker, b"Local cleanup is incomplete. Do not upload.\n")
    # Guards and rescued LOCAL preparation are durable before deleting old responses.
    for output in sorted(plan.guards):
        _inside(plan, output / GUARD_NAME)
        ensure_guard(output)
    for path, content in sorted(plan.rewrites.items()):
        _inside(plan, path)
        write_bytes(path, content)
    for path in sorted(plan.deletes):
        _inside(plan, path)
        path.unlink(missing_ok=True)
    for path, content in sorted(plan.upgrades.items()):
        _inside(plan, path)
        write_bytes(path, content)
    remaining = inspect_migration(plan.roots, plan.storage)
    if remaining.issues or remaining.deletes or remaining.rewrites or remaining.upgrades:
        raise AppError("Cleanup is incomplete. Run migration review again; uploading remains blocked.")
    for marker in markers:
        _inside(plan, marker)
        marker.unlink(missing_ok=True)
