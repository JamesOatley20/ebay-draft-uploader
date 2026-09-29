"""Prepare local files; keep every eBay response and upload outcome in memory."""

from dataclasses import dataclass, field
from hashlib import sha256
from html import escape
from pathlib import Path

from . import AppError, SessionStopped
from .auth import AuthExpired
from .ebay import APIError, Ebay, UncertainWrite, cache_is_fresh
from .feed import make_preparation_csv, make_upload_csv, parse_result
from .files import read_bytes, write_bytes, write_text, workspace, load_batch
from .guards import arm_guard, is_guarded
from .images import PHOTO_EXTENSIONS, UNSUPPORTED_PHOTO_EXTENSIONS, MAX_SOURCE_BYTES, Photo, normalize_photo
from .listing import Listing, read_json
from .notes import SellerNotes, update_preparation

STATUS_TEXT = {
    "working": "Working. Keep this window open to receive the result.",
    "pending": "eBay is processing. Stopping loses this session's task reference; remote work may continue.",
    "accepted": "eBay accepted the draft row. Review the actual draft in Seller Hub before publishing.",
    "rejected": "eBay rejected the row. The queue has stopped. Check Seller Hub Reports and resolve the error before another attempt.",
    "needs_review": "The outcome needs checking in Seller Hub. Do not submit a second copy.",
    "stopped": "Stopped locally. Remote work may continue. Check Seller Hub before another attempt.",
    "error": "The session could not continue. Check Seller Hub before another attempt.",
    "guarded": "Held by a local guard. Review Seller Hub before explicitly releasing it.",
    "not_attempted": "Not attempted in this session.",
}


@dataclass
class PreparedItem:
    folder: Path
    output: Path
    listing: Listing
    notes: SellerNotes
    photos: list[tuple[str, Path, str]] = field(default_factory=list)
    input_hashes: dict[str, str] = field(default_factory=dict)


@dataclass(repr=False)
class RuntimeItem:
    """Never serialise this object or send it to the local-file reporting code."""
    task_id: str = ""
    images: dict = field(default_factory=dict)
    status: str = "working"
    messages: list[str] = field(default_factory=list)


@dataclass(repr=False)
class SessionResult:
    name: str
    status: str
    messages: list[str] = field(default_factory=list)


def prepare_item(root: Path, folder: Path) -> PreparedItem:
    output = workspace(root, folder.name)
    notes = SellerNotes.read(folder)
    listing_bytes = read_bytes(folder / "listing.json", 256_000)
    try:
        listing = Listing.parse(read_json(listing_bytes.decode("utf-8-sig")))
    except UnicodeError:
        raise AppError("Save listing.json as UTF-8.") from None
    item = PreparedItem(folder, output, listing, notes)
    candidates = sorted((p for p in folder.iterdir() if not p.name.startswith(".")
                         and p.suffix.lower() in PHOTO_EXTENSIONS), key=lambda p: (p.name.casefold(), p.name))
    unsupported = [p.name for p in folder.iterdir() if p.suffix.lower() in UNSUPPORTED_PHOTO_EXTENSIONS]
    if unsupported:
        raise AppError("Unsupported photo type: " + ", ".join(unsupported) + ". No photos were silently omitted.")
    if not 1 <= len(candidates) <= 12:
        raise AppError("Provide 1 to 12 photos for this item.")
    if len({p.name.casefold() for p in candidates}) != len(candidates):
        raise AppError("Two photo names differ only by capitals. Give them distinct names.")
    notes_bytes = read_bytes(folder / "input.txt", 32_000)
    item.input_hashes = {"listing.json": sha256(listing_bytes).hexdigest(), "input.txt": sha256(notes_bytes).hexdigest()}
    photo_notes = []
    for index, path in enumerate(candidates, 1):
        source = read_bytes(path, MAX_SOURCE_BYTES)
        item.input_hashes[path.name] = sha256(source).hexdigest()
        photo = normalize_photo(source, path.name)
        preview = output / "photos" / f"{index:02}.jpg"
        write_bytes(preview, photo.content)
        item.photos.append((path.name, preview, photo.digest))
        photo_notes.append(f"{path.name}: {photo.width} x {photo.height} local JPEG. " + " ".join(photo.notes))
    write_bytes(output / "draft.csv", make_preparation_csv(listing, "local-" + output.name))
    update_preparation(folder, ["Offline checks passed. No eBay request was made.",
                                "draft.csv is a preparation export without uploaded photo URLs.",
                                "Main photo: " + item.photos[0][0], *photo_notes], listing, notes)
    return item


def check_reviewed_files(item: PreparedItem) -> None:
    photos = {p.name for p in item.folder.iterdir() if not p.name.startswith(".")
              and p.suffix.lower() in PHOTO_EXTENSIONS | UNSUPPORTED_PHOTO_EXTENSIONS}
    if photos != set(item.input_hashes) - {"listing.json", "input.txt"}:
        raise AppError("The photos changed during review. Close this run and preview again.")
    for name, digest in item.input_hashes.items():
        if sha256(read_bytes(item.folder / name, MAX_SOURCE_BYTES)).hexdigest() != digest:
            raise AppError("Local inputs changed during review. Close this run and preview again.")


def prepare_batch(root: Path) -> tuple[list[PreparedItem], dict[str, str]]:
    folders, skipped = load_batch(root)
    items = []
    problems = dict(skipped)
    for folder in folders:
        try:
            items.append(prepare_item(root, folder))
        except AppError as error:
            problems[folder.name] = str(error)
        except OSError:
            problems[folder.name] = "Could not read or prepare this item's local files."
    for name, reason in problems.items():
        folder = root / name
        notes = None
        try:
            notes = SellerNotes.read(folder)
        except (AppError, OSError):
            pass
        update_preparation(folder, ["Local preparation needs attention.", reason], notes=notes)
    write_preview(root, items, problems)
    return items, problems


def write_preview(root: Path, items: list[PreparedItem], problems: dict[str, str]) -> None:
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">',
             '<title>eBay draft preparation</title><style>body{font:18px/1.5 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:0 20px}',
             'article{border-top:1px solid #bbb;padding:24px 0}img{max-width:230px;max-height:210px;margin:5px}a{overflow-wrap:anywhere}',
             '.source{font-size:14px;color:#555;overflow-wrap:anywhere}.title-count{font-size:14px;color:#555}',
             '</style><h1>Your local draft preparation</h1>',
             '<p>This preview contains local preparation only. It does not record upload outcomes. Review Seller Hub before another attempt.</p>']
    for item in items:
        listing = item.listing
        price = f'GBP {listing.price_gbp:.2f}' if listing.price_gbp is not None else 'Price to be added on eBay'
        parts += ['<article><h2>' + escape(listing.title) + '</h2>',
                  f'<p class="title-count">Listing title: {len(listing.title)} / 80 characters</p>',
                  '<p class="source">Local folder (not uploaded as the title): ' + escape(item.folder.name) + '</p>',
                  '<p>' + price + '</p><p>' + escape(listing.description) + '</p>']
        for name, photo, _ in item.photos:
            relative = photo.relative_to(workspace(root)).as_posix()
            parts.append(f'<img src="{escape(relative, quote=True)}" alt="{escape(name, quote=True)}">')
        parts.append(f'<p><a href="{escape((item.folder / "output.txt").as_uri(), quote=True)}">Open output.txt</a></p></article>')
    for name, reason in problems.items():
        parts.append('<article><h2>' + escape(name) + '</h2><p>Not ready: ' + escape(reason) + '</p></article>')
    parts.append('</html>')
    write_text(workspace(root) / "preview.html", "\n".join(parts))


def poll_task(api: Ebay, runtime: RuntimeItem, emit) -> None:
    attempt = 0
    while True:
        api.check_cancelled()
        task = api.get_task(runtime.task_id)
        if task.get("taskId", runtime.task_id) != runtime.task_id or task.get("feedType", "FX_LISTING") != "FX_LISTING":
            raise AppError("eBay returned a different task. Check Seller Hub.")
        remote = task.get("status")
        if remote in {"COMPLETED", "COMPLETED_WITH_ERROR"}:
            result = parse_result(api.get_result(runtime.task_id))
            runtime.status = {"success": "accepted", "rejected": "rejected", "unknown": "needs_review"}[result.status]
            runtime.messages = [api.auth.redact(m[:2000]) for m in result.messages[:20]]
            return
        if remote in {"FAILED", "ABORTED", "ERROR"} or not isinstance(remote, str):
            runtime.status = "needs_review"
            return
        runtime.status = "pending"
        if attempt == 0:
            emit("pending", [])
        api.sleep(min(30, 3 * 2 ** min(attempt, 4)))
        attempt += 1


def submit_item(api: Ebay, item: PreparedItem, emit=lambda status, messages: None) -> SessionResult:
    api.check_cancelled()
    if is_guarded(item.output):
        return SessionResult(item.folder.name, "guarded")
    check_reviewed_files(item)
    # Only fixed LOCAL bytes are written after authentication. No response affects them.
    arm_guard(item.output)
    runtime = RuntimeItem()
    try:
        urls = []
        for name, path, digest in item.photos:
            api.check_cancelled()
            content = read_bytes(path, 12 * 1024 * 1024)
            if sha256(content).hexdigest() != digest:
                raise AppError("A local photo changed. Review the files before another attempt.")
            record = runtime.images.get(digest)
            if not cache_is_fresh(record):
                record = api.upload_photo(Photo(name, content, digest, 0, 0))
                runtime.images[digest] = record
            urls.append(record["url"])
        csv_content = make_upload_csv(item.listing, urls, "local-" + item.output.name)
        runtime.task_id = api.create_task()
        try:
            api.upload_draft(runtime.task_id, csv_content)
        except UncertainWrite:
            # While this process lives we can still check the known task.
            emit("pending", ["Upload acknowledgement was uncertain. Checking the same task without resending."])
        poll_task(api, runtime, emit)
        return SessionResult(item.folder.name, runtime.status, runtime.messages)
    finally:
        runtime.images.clear()
        runtime.task_id = ""
        runtime.messages = []


def submit_batch(api: Ebay, items: list[PreparedItem], emit=lambda result: None) -> list[SessionResult]:
    results = []
    stopped = False
    for item in items:
        if stopped or api.cancelled():
            result = SessionResult(item.folder.name, "not_attempted")
        else:
            emit(SessionResult(item.folder.name, "working"))
            try:
                result = submit_item(api, item, lambda status, messages: emit(SessionResult(item.folder.name, status, messages)))
            except SessionStopped:
                result = SessionResult(item.folder.name, "stopped")
                stopped = True
            except AuthExpired:
                result = SessionResult(item.folder.name, "error", ["The User token expired or was refused. Start a new session only after checking Seller Hub."])
                stopped = True
            except APIError as error:
                result = SessionResult(item.folder.name, "needs_review", [api.auth.redact(error.detail)])
                stopped = True
            except (AppError, OSError):
                result = SessionResult(item.folder.name, "needs_review", ["The session could not safely complete this item. Check Seller Hub before another attempt."])
                stopped = True
            # A row rejection can indicate a problem with the shared feed route,
            # not just this item's fields. Do not send the rest of the batch.
            if result.status in {"rejected", "needs_review"}:
                stopped = True
        results.append(result)
        emit(result)
    return results
