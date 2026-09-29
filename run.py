"""Windows entry point. Local preparation on disk; eBay session data in memory."""

from contextlib import ExitStack
from pathlib import Path
import argparse
import os
import sys
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ebay_drafts import AppError, __version__
from ebay_drafts.files import batch_lock, check_path, component, read_bytes, write_text, workspace


def pick_batch() -> Path:
    import tkinter as tk
    from tkinter import filedialog
    window = tk.Tk()
    window.withdraw()
    window.attributes("-topmost", True)
    window.report_callback_exception = lambda *_: window.quit()
    try:
        selected = filedialog.askdirectory(title="Choose the folder containing batch.json and your item folders", parent=window)
    finally:
        window.destroy()
    if not selected:
        raise AppError("No folder selected. Nothing was uploaded.")
    return Path(selected)


def batch_root(path: Path) -> Path:
    check_path(path)
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise AppError("Choose an extracted batch folder, not a ZIP file.")
    return root


class PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # Never echo unrecognised arguments: someone might mistakenly paste a token.
        raise AppError("Invalid command arguments. Use --help. Never supply tokens on the command line.")


def migrate(roots: list[Path]) -> int:
    from ebay_drafts.migration import app_storage, inspect_migration, apply_migration
    roots = sorted({batch_root(root) for root in roots})
    with ExitStack() as locks:
        for root in roots:
            locks.enter_context(batch_lock(root))
        plan = inspect_migration(roots, app_storage())
        print("\nMigration checks only the named batch roots and this user's eBayDrafts app storage.")
        print("Close older app versions first. Review unresolved uploads in Seller Hub before cleanup.")
        for line in plan.describe():
            print(line)
        if plan.issues:
            print("Resolve the REVIEW entries locally, then run migration again. Nothing was deleted.")
            return 2
        if not plan.needed:
            print("No legacy files were found in these locations.")
            return 0
        print("This removes old API data without making backup copies. Authored preparation files are preserved.")
        print("Other batches and external backups are outside this cleanup.")
        if input("Type MIGRATE to apply this exact cleanup, or Enter to cancel: ").strip() != "MIGRATE":
            print("Migration cancelled.")
            return 0
        apply_migration(plan)
        print("Migration completed for the listed locations. Each new upload session needs a User token.")
    return 0


def main() -> int:
    parser = PrivateArgumentParser(description="Create eBay UK drafts with session-only authentication. Nothing is published.")
    parser.add_argument("--batch", type=Path, help="Folder containing batch.json and item folders")
    parser.add_argument("--migration-batch", action="append", type=Path, default=[],
                        help="Additional explicit batch root, only with --migrate; may be repeated")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--preview", action="store_true", help="Prepare files offline without authentication or uploading")
    actions.add_argument("--migrate", action="store_true", help="Review and clean legacy data; without --batch, inspect app sign-in storage only")
    actions.add_argument("--release", metavar="ITEM_FOLDER", help="Release a local guard after manually resolving the outcome in Seller Hub")
    actions.add_argument("--register", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.migration_batch and not args.migrate:
        raise AppError("--migration-batch can only be used with --migrate.")
    if args.register:
        if os.name != "nt" or not os.environ.get("LOCALAPPDATA"):
            raise AppError("Setup.cmd registration is for Windows.")
        write_text(Path(os.environ["LOCALAPPDATA"]) / "eBayDrafts" / "tool-path.txt", str(Path(__file__).resolve()))
        print("Setup complete. Double-click Start.cmd to begin.")
        return 0
    if args.migrate:
        return migrate(([args.batch] if args.batch else []) + args.migration_batch)
    if not args.batch and not args.preview and not args.release:
        print(f"\neBay Drafts {__version__}\n1. Open a batch and review/create drafts\n2. Review migration of old data\n3. Release an item after checking Seller Hub\nEnter. Exit")
        choice = input("Choose: ").strip()
        if choice == "2":
            return migrate([pick_batch()])
        if choice == "3":
            args.batch = pick_batch()
            args.release = input("Exact item folder name: ").strip()
        elif choice != "1":
            return 0
    root = batch_root(args.batch or pick_batch())
    from ebay_drafts.migration import app_storage, require_clean
    from ebay_drafts.guards import is_guarded, release_guard
    from ebay_drafts.workflow import prepare_batch
    with batch_lock(root):
        require_clean(root, app_storage())
        if args.release:
            folder = root / component(args.release)
            check_path(folder)
            if not folder.is_dir():
                raise AppError("That immediate item folder does not exist in this batch.")
            print("Review Seller Hub drafts and Reports. Establish that no existing draft or still-processing upload would be duplicated.")
            print("An absent draft alone is not proof while processing may continue. If uncertain, leave the guard and contact eBay support.")
            if input("Type RELEASE only after resolving this, or Enter to cancel: ").strip() == "RELEASE":
                release_guard(workspace(root, folder.name))
                print("Local guard released. Review the item again before a new attempt.")
            return 0
        reviewed_batch = read_bytes(root / "batch.json", 256_000)
        items, problems = prepare_batch(root)
        ready = [item for item in items if not is_guarded(item.output)]
        print(f"\nReady for a new attempt: {len(ready)}. Held by local guards: {len(items) - len(ready)}. Need preparation: {len(problems)}.")
        for name, reason in problems.items():
            print(name + ": " + reason)
        preview = workspace(root) / "preview.html"
        print("Local preparation: " + str(preview))
        if args.preview:
            print("Offline preview only. No eBay connection was made.")
            return 1 if problems else 0
        webbrowser.open(preview.as_uri())
        if not ready:
            print("No unguarded items are ready. Review Seller Hub before releasing an item.")
            return 1 if problems else 0
        print("Review the preparation. A token is needed for this run. Closing loses task references; remote work may continue.")
        if input("Type DRAFT to continue, or press Enter to stop: ").strip() != "DRAFT":
            print("Stopped before authentication. Nothing was uploaded.")
            return 0
        if read_bytes(root / "batch.json", 256_000) != reviewed_batch:
            raise AppError("The batch changed during review. Start again.")
        require_clean(root, app_storage())
        from ebay_drafts.session_ui import run_session
        results = run_session(ready)
        # Only a fixed message goes to redirectable output; results stay in native UI.
        print("Session window closed. Check Seller Hub before another attempt. output.txt contains preparation only.")
        if any(result.status in {"error", "rejected", "needs_review"} for result in results):
            return 1
        return 3 if any(result.status in {"pending", "stopped", "not_attempted"} for result in results) else (1 if problems else 0)


def entry() -> int:
    try:
        if sys.version_info < (3, 11):
            raise AppError("Install Python 3.11 or newer, then run Setup.cmd again.")
        return main()
    except KeyboardInterrupt:
        print("\nStopped locally. Remote uploads may continue. Check Seller Hub before another attempt.")
        return 130
    except AppError as error:
        print("\nCannot continue: " + str(error), file=sys.stderr)
        return 2
    except Exception:
        # No unhandled traceback, exception repr, request URL or response on disk/stdout.
        print("\nCannot continue safely. Check local setup and Seller Hub before another attempt.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(entry())
