import contextlib
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import uuid
from unittest.mock import patch

from ebay_drafts import files
from ebay_drafts.guards import GUARD_BYTES, GUARD_NAME, release_guard
from ebay_drafts.workflow import submit_batch
from support import BatchTest, Service

AUDIT_WRITES = None


def audit(event, args):
    if AUDIT_WRITES is not None and event == "open":
        path, mode, flags = args
        if isinstance(path, (str, bytes)) and ((isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)) or (mode and any(c in mode for c in "wax+"))):
            AUDIT_WRITES.append(Path(os.fsdecode(path)))


sys.addaudithook(audit)


class PersistenceTests(BatchTest):
    def test_every_runtime_write_contains_only_fixed_guard_bytes(self):
        global AUDIT_WRITES
        items = self.prepared()
        for outcome in ("success", "rejected", "feed-rejected", "malformed", "photo-error", "401", "upload-timeout"):
            service = Service(outcome=outcome)
            original = files.write_bytes
            writes = []
            def writer(path, content):
                writes.append((path, content))
                self.assertEqual(path.name, GUARD_NAME)
                self.assertEqual(content, GUARD_BYTES)
                return original(path, content)
            output = io.StringIO()
            AUDIT_WRITES = []
            try:
                with patch("ebay_drafts.guards.write_bytes", writer), patch("ebay_drafts.files.write_bytes", writer), patch("ebay_drafts.workflow.write_bytes", writer), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), service.api() as api:
                    submit_batch(api, items)
                opened = list(AUDIT_WRITES)
            finally:
                AUDIT_WRITES = None
            self.assertEqual(len(writes), 1)
            self.assertEqual(output.getvalue(), "")
            self.assertTrue(opened)
            for path in opened:
                self.assertEqual(path.parent, items[0].output)
                self.assertTrue(path.name.startswith(".tmp-") or path.name == GUARD_NAME)
            self.assert_no_runtime(service.prohibited)
            release_guard(items[0].output)

    def test_force_termination_needs_no_cleanup_handler(self):
        child = Path(__file__).with_name("interrupt_child.py")
        for stage in ("photo", "task", "upload", "pending", "result", "completed"):
            with self.subTest(stage=stage):
                service = Service(seed=uuid.uuid4().hex)
                proc = subprocess.Popen([sys.executable, "-I", "-B", str(child)],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, encoding="utf-8", cwd=self.home)
                try:
                    proc.stdin.write(json.dumps({"root": str(self.root), "seed": service.seed, "stage": stage}) + "\n")
                    proc.stdin.flush()
                    proc.stdin.close()
                    lines = queue.Queue()
                    threading.Thread(target=lambda: lines.put(proc.stdout.readline()), daemon=True).start()
                    reached = lines.get(timeout=15).strip()
                    self.assertEqual(reached, stage)
                    proc.kill()  # TerminateProcess on Windows: no finally/atexit runs.
                    proc.wait(timeout=5)
                    self.assertEqual(proc.stderr.read(), "")
                    self.assert_no_runtime(service.prohibited)
                    guard = next(self.root.rglob(GUARD_NAME))
                    self.assertEqual(guard.read_bytes(), GUARD_BYTES)
                    release_guard(guard.parent)
                finally:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=5)
                    for stream in (proc.stdin, proc.stdout, proc.stderr):
                        if stream:
                            stream.close()
