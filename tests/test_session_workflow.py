import threading
from unittest.mock import patch

from ebay_drafts.guards import GUARD_BYTES, GUARD_NAME, release_guard
from ebay_drafts.workflow import submit_batch
from support import BatchTest, Service, make_batch


class SessionTests(BatchTest):
    def test_rejection_stops_before_any_remote_work_on_later_items(self):
        make_batch(self.root, names=("Camera", "Lens", "Strap"))
        for outcome in ("rejected", "feed-rejected"):
            with self.subTest(outcome=outcome):
                items = self.prepared()
                service = Service(outcome=outcome)
                events = []
                with service.api() as api:
                    results = submit_batch(api, items, events.append)
                self.assertEqual([r.status for r in results],
                                 ["rejected", "not_attempted", "not_attempted"])
                for suffix in ("/create_image_from_file", "/task", "/upload_file"):
                    self.assertEqual(sum(method == "POST" and path.endswith(suffix)
                                         for method, path in service.calls), 1)
                self.assertEqual((items[0].output / GUARD_NAME).read_bytes(), GUARD_BYTES)
                self.assertFalse(any((item.output / GUARD_NAME).exists() for item in items[1:]))
                if outcome == "feed-rejected":
                    self.assertIn("errorcode: BAF.Error.5", results[0].messages)
                self.assertNotIn(service.token, str([event.messages for event in events]))
                self.assert_no_runtime(service.prohibited)
                release_guard(items[0].output)

    def test_success_still_advances_to_next_item(self):
        make_batch(self.root, names=("Camera", "Lens"))
        service = Service()
        with service.api() as api:
            results = submit_batch(api, self.prepared())
        self.assertEqual([r.status for r in results], ["accepted", "accepted"])
        self.assertEqual(sum(path.endswith("/upload_file") for _, path in service.calls), 2)
        self.assert_no_runtime(service.prohibited)

    def test_success_and_rejection_same_local_guard(self):
        items = self.prepared()
        for outcome, expected in (("success", "accepted"), ("rejected", "rejected")):
            service = Service(outcome=outcome)
            with service.api() as api:
                results = submit_batch(api, items)
            self.assertEqual(results[0].status, expected)
            self.assertEqual((items[0].output / GUARD_NAME).read_bytes(), GUARD_BYTES)
            self.assertIn(service.url.encode(), service.upload)
            self.assert_no_runtime(service.prohibited)
            release_guard(items[0].output)

    def test_guard_precedes_every_remote_write_and_rerun_sends_nothing(self):
        items = self.prepared()
        service = Service()
        service.on_photo = lambda: self.assertEqual((items[0].output / GUARD_NAME).read_bytes(), GUARD_BYTES)
        with service.api() as api:
            submit_batch(api, items)
            count = len(service.calls)
            self.assertEqual(submit_batch(api, items)[0].status, "guarded")
            self.assertEqual(len(service.calls), count)
        (self.root / "Camera" / "input.txt").write_text("Changed seller note", encoding="utf-8")
        items = self.prepared()
        with service.api() as api:
            self.assertEqual(submit_batch(api, items)[0].status, "guarded")

    def test_ambiguous_upload_is_polled_without_reposting(self):
        service = Service(outcome="upload-timeout")
        with service.api() as api:
            results = submit_batch(api, self.prepared())
        self.assertEqual(results[0].status, "accepted")
        self.assertEqual(sum(path.endswith("/upload_file") for method, path in service.calls), 1)
        self.assert_no_runtime(service.prohibited)

    def test_bad_results_hold_and_stop_remaining_queue(self):
        make_batch(self.root, names=("Camera", "Lens"))
        for outcome in ("malformed", "photo-error", "401"):
            items = self.prepared()
            service = Service(outcome=outcome)
            with service.api() as api:
                result = submit_batch(api, items)
            self.assertIn(result[0].status, {"needs_review", "error"})
            self.assertEqual(result[1].status, "not_attempted")
            self.assertEqual(sum(path.endswith("/upload_file") for method, path in service.calls), int(outcome != "photo-error"))
            self.assert_no_runtime(service.prohibited)
            release_guard(items[0].output)

    def test_cancel_before_start_has_no_remote_write_or_guard(self):
        items = self.prepared()
        service = Service()
        with service.api(cancelled=lambda: True) as api:
            results = submit_batch(api, items)
        self.assertEqual(results[0].status, "not_attempted")
        self.assertFalse(service.calls)
        self.assertFalse((items[0].output / GUARD_NAME).exists())

    def test_stop_while_pending_keeps_guard_only(self):
        items = self.prepared()
        stop = threading.Event()
        service = Service(outcome="pending")
        service.on_poll = stop.set
        with service.api(cancelled=stop.is_set) as api:
            result = submit_batch(api, items)
        self.assertEqual(result[0].status, "stopped")
        self.assertEqual((items[0].output / GUARD_NAME).read_bytes(), GUARD_BYTES)
        self.assert_no_runtime(service.prohibited)

    def test_changed_inputs_never_upload(self):
        items = self.prepared()
        (self.root / "Camera" / "input.txt").write_text("edited", encoding="utf-8")
        service = Service()
        with service.api() as api:
            submit_batch(api, items)
        self.assertFalse(service.calls)
        self.assertFalse((items[0].output / GUARD_NAME).exists())
