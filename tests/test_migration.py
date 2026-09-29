import json
from pathlib import Path
from unittest.mock import patch

from ebay_drafts import AppError
from ebay_drafts.feed import make_upload_csv
from ebay_drafts.files import workspace, load_batch
from ebay_drafts.guards import GUARD_BYTES, GUARD_NAME
from ebay_drafts.listing import Listing
from ebay_drafts.migration import inspect_migration, apply_migration, require_clean, MARKER
from ebay_drafts.notes import STATUS_MARKER
from support import BatchTest, LISTING


class MigrationTests(BatchTest):
    def test_mention_of_old_marker_in_authored_prose_is_preserved(self):
        path = self.root / "Camera" / "output.txt"
        content = ("My note mentions " + STATUS_MARKER + " as text, not a section.\n").encode()
        path.write_bytes(content)
        plan = inspect_migration([self.root], self.storage)
        self.assertFalse(plan.needed)
        self.assertEqual(path.read_bytes(), content)

    def test_root_manifest_temp_is_cleaned_after_interrupted_upgrade(self):
        leftover = self.root / ".tmp-abcdefgh"
        leftover.write_bytes((self.root / "batch.json").read_bytes())
        plan = inspect_migration([self.root], self.storage)
        self.assertIn(leftover, plan.deletes)
        apply_migration(plan)
        self.assertFalse(leftover.exists())
        require_clean(self.root, self.storage)

    def test_unrecognised_root_temp_is_not_deleted(self):
        leftover = self.root / ".tmp-abcdefgh"
        leftover.write_text("Unrelated content")
        plan = inspect_migration([self.root], self.storage)
        self.assertTrue(plan.issues)
        with self.assertRaises(AppError):
            apply_migration(plan)
        self.assertEqual(leftover.read_text(), "Unrelated content")

    def legacy(self):
        manifest = self.root / "batch.json"
        batch = json.loads(manifest.read_text())
        batch["version"] = 2
        manifest.write_text(json.dumps(batch), encoding="utf-8")
        output = workspace(self.root, "Camera")
        self.secret = "historical-private-value"
        self.state = {"version": 2, "task_id": self.secret, "previous_tasks": [self.secret],
                      "status": "pending", "messages": [self.secret],
                      "images": {"local": {"url": "https://i.ebayimg.com/" + self.secret}},
                      "listing": LISTING, "seller_notes": "Seller's original notes"}
        (output / "state.json").write_text(json.dumps(self.state), encoding="utf-8")
        (output / "result.bin").write_bytes(self.secret.encode())
        (output / ".tmp-abcdefgh").write_bytes(self.secret.encode())
        (output / "draft.csv").write_bytes(make_upload_csv(Listing.parse(LISTING), ["https://i.ebayimg.com/" + self.secret], "local-test"))
        self.authored = (self.root / "Camera" / "output.txt").read_bytes()
        with (self.root / "Camera" / "output.txt").open("ab") as stream:
            stream.write((STATUS_MARKER + "\n" + self.secret).encode())
        (self.root / ".ebay-drafts" / "preview.html").write_text("Old status " + self.secret)
        self.storage.mkdir(parents=True)
        (self.storage / "sign-in.bin").write_bytes(self.secret.encode())
        (self.storage / ".tmp-ijklmnop").write_bytes(self.secret.encode())
        (self.storage / "tool-path.txt").write_text("C:\\local\\run.py")
        return output

    def test_cleans_all_known_paths_without_altering_authored_files(self):
        output = self.legacy()
        originals = {p: p.read_bytes() for p in (self.root / "Camera").iterdir() if p.name != "output.txt"}
        plan = inspect_migration([self.root], self.storage)
        self.assertFalse(plan.issues)
        self.assertNotIn(self.secret, "\n".join(plan.describe()))
        apply_migration(plan)
        for path, content in originals.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual((self.root / "Camera" / "output.txt").read_bytes(), self.authored)
        self.assertEqual((output / GUARD_NAME).read_bytes(), GUARD_BYTES)
        self.assertTrue((self.storage / "tool-path.txt").exists())
        self.assertEqual(json.loads((self.root / "batch.json").read_text())["version"], 3)
        self.assert_no_runtime([self.secret])
        require_clean(self.root, self.storage)
        self.assertFalse(inspect_migration([self.root], self.storage).needed)

    def test_recovers_only_local_snapshot_fields_when_originals_missing(self):
        self.legacy()
        (self.root / "Camera" / "listing.json").unlink()
        (self.root / "Camera" / "input.txt").unlink()
        apply_migration(inspect_migration([self.root], self.storage))
        self.assertEqual(json.loads((self.root / "Camera" / "listing.json").read_text()), LISTING)
        self.assertEqual((self.root / "Camera" / "input.txt").read_text(), self.state["seller_notes"])
        self.assert_no_runtime([self.secret])

    def test_orphan_storage_rescues_local_content_and_removes_runtime(self):
        output = self.legacy()
        orphan = self.root / ".ebay-drafts" / ("a" * 24)
        orphan.mkdir()
        (orphan / "state.json").write_text(json.dumps(self.state))
        apply_migration(inspect_migration([self.root], self.storage))
        self.assertEqual(json.loads((orphan / "recovered-listing.json").read_text()), LISTING)
        self.assertEqual((orphan / GUARD_NAME).read_bytes(), GUARD_BYTES)
        self.assert_no_runtime([self.secret])

    def test_unknown_backup_blocks_without_deleting_anything(self):
        output = self.legacy()
        (output / "state.json.bak").write_text(self.secret)
        plan = inspect_migration([self.root], self.storage)
        self.assertTrue(plan.issues)
        with self.assertRaises(AppError):
            apply_migration(plan)
        self.assertTrue((output / "state.json").exists())
        self.assertTrue((self.storage / "sign-in.bin").exists())

    def test_authored_api_records_are_reported_not_silently_deleted(self):
        self.legacy()
        target = self.root / "Camera" / "output.txt"
        content = b'Private seller note\n{"access_token":"do-not-erase-without-review"}\n'
        target.write_bytes(content)
        plan = inspect_migration([self.root], self.storage)
        self.assertTrue(plan.issues)
        with self.assertRaises(AppError):
            apply_migration(plan)
        self.assertEqual(target.read_bytes(), content)

    def test_review_snapshot_must_still_match(self):
        output = self.legacy()
        plan = inspect_migration([self.root], self.storage)
        (output / "result.bin").write_bytes(b"changed")
        with self.assertRaises(AppError):
            apply_migration(plan)
        self.assertTrue((output / "state.json").exists())

    def test_interrupted_cleanup_stays_blocked_then_resumes(self):
        output = self.legacy()
        plan = inspect_migration([self.root], self.storage)
        original = Path.unlink
        def fail(path, *args, **kwargs):
            if path.name == "result.bin":
                raise PermissionError("simulated")
            return original(path, *args, **kwargs)
        with patch.object(Path, "unlink", fail), self.assertRaises(PermissionError):
            apply_migration(plan)
        self.assertTrue((self.root / ".ebay-drafts" / MARKER).exists())
        self.assertTrue((output / GUARD_NAME).exists())
        with self.assertRaises(AppError):
            require_clean(self.root, self.storage)
        apply_migration(inspect_migration([self.root], self.storage))
        require_clean(self.root, self.storage)
        self.assert_no_runtime([self.secret])

    def test_scope_does_not_include_neighbouring_files(self):
        self.legacy()
        outside = self.home / "unrelated-backup.bin"
        outside.write_text("do not touch")
        apply_migration(inspect_migration([self.root], self.storage))
        self.assertEqual(outside.read_text(), "do not touch")

    def test_executor_refuses_injected_out_of_scope_target(self):
        self.legacy()
        outside = self.home / "unrelated-backup.bin"
        outside.write_text("do not touch")
        plan = inspect_migration([self.root], self.storage)
        plan.deletes.add(outside)
        with self.assertRaises(AppError):
            apply_migration(plan)
        self.assertEqual(outside.read_text(), "do not touch")

    def test_symlink_is_never_followed(self):
        self.legacy()
        outside = self.home / "unrelated.txt"
        outside.write_text("untouched")
        link = self.root / ".ebay-drafts" / "linked"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("Windows symlink privilege not available")
        with self.assertRaises(AppError):
            inspect_migration([self.root], self.storage)
        self.assertEqual(outside.read_text(), "untouched")

    def test_clean_v2_batch_only_changes_manifest_version(self):
        batch_path = self.root / "batch.json"
        data = json.loads(batch_path.read_text())
        data["version"] = 2
        batch_path.write_text(json.dumps(data))
        with self.assertRaises(AppError):
            load_batch(self.root)
        plan = inspect_migration([self.root], self.storage)
        self.assertFalse(plan.guards)
        apply_migration(plan)
        new = json.loads(batch_path.read_text())
        self.assertEqual(new, {**data, "version": 3})
        load_batch(self.root)
