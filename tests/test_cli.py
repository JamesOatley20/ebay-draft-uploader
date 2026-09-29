import json
import os
from pathlib import Path
import subprocess
import sys

from ebay_drafts.files import batch_lock
from support import BatchTest


class CLITests(BatchTest):
    def command(self, *args, input=""):
        env = dict(os.environ, LOCALAPPDATA=str(self.home / "localapp"))
        return subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve().parents[1] / "run.py"),
                               "--batch", str(self.root), *args],
                              input=input, text=True, encoding="utf-8", errors="replace",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=20)

    def test_preview_works_while_windows_batch_lock_is_held(self):
        result = self.command("--preview")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Offline preview only", result.stdout)

    def test_second_process_cannot_use_a_locked_batch(self):
        with batch_lock(self.root):
            result = self.command("--preview")
        self.assertEqual(result.returncode, 2)
        self.assertIn("already open", result.stderr)

    def test_migration_works_through_real_cli_and_lock(self):
        path = self.root / "batch.json"
        batch = json.loads(path.read_text())
        batch["version"] = 2
        path.write_text(json.dumps(batch))
        cancelled = self.command("--migrate", input="\n")
        self.assertEqual(cancelled.returncode, 0, cancelled.stdout + cancelled.stderr)
        self.assertEqual(json.loads(path.read_text())["version"], 2)
        migrated = self.command("--migrate", input="MIGRATE\n")
        self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
        self.assertEqual(json.loads(path.read_text())["version"], 3)
