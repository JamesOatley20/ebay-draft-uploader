import contextlib
import io
import tkinter as tk
from unittest.mock import patch

import httpx

from ebay_drafts.session_ui import run_session
from support import BatchTest, Service


class SessionUITests(BatchTest):
    def hidden_root(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tk display unavailable")
        root.withdraw()
        self.addCleanup(lambda: self.destroy(root))
        return root

    @staticmethod
    def destroy(root):
        try:
            root.destroy()
        except tk.TclError:
            pass

    def test_token_cancel_never_starts_client(self):
        root = self.hidden_root()
        output = io.StringIO()
        with patch("tkinter.Tk", return_value=root), patch("tkinter.simpledialog.askstring", return_value=None), patch("ebay_drafts.session_ui.make_client") as client, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(run_session(self.prepared()), [])
            client.assert_not_called()
        self.assertEqual(output.getvalue(), "")
        self.assertFalse(list(self.root.rglob("submission-guard.json")))

    def run_hidden(self, service=None, failure=None, stop_early=False):
        root = self.hidden_root()
        output = io.StringIO()
        if service is None:
            service = Service()
        def client():
            if failure:
                raise RuntimeError(failure)
            return httpx.Client(transport=httpx.MockTransport(service.handle), trust_env=False)
        def tick():
            try:
                buttons = [child for frame in root.winfo_children() for child in frame.winfo_children()
                           if isinstance(child, tk.Button)]
                for button in buttons:
                    if button.cget("text") == "Close":
                        button.invoke()
                        return
                    if stop_early and button.cget("text") == "Stop this session":
                        button.invoke()
                root.after(30, tick)
            except tk.TclError:
                pass
        root.after(30, tick)
        root.after(5000, root.quit)
        with patch("tkinter.Tk", return_value=root), patch.object(root, "deiconify"), patch("tkinter.simpledialog.askstring", return_value=service.token), patch("ebay_drafts.session_ui.make_client", side_effect=client), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            results = run_session(self.prepared())
        self.assertEqual(output.getvalue(), "")
        self.assert_no_runtime(service.prohibited)
        return results

    def test_real_tk_lifecycle_uses_only_in_memory_results(self):
        results = self.run_hidden()
        self.assertEqual(results[0].status, "accepted")

    def test_real_tk_stop_ends_pending_worker(self):
        results = self.run_hidden(Service(outcome="pending"), stop_early=True)
        self.assertIn(results[0].status, {"stopped", "not_attempted"})

    def test_unexpected_worker_exception_never_prints(self):
        results = self.run_hidden(failure="private-error-canary")
        self.assertEqual(results[0].status, "error")
        self.assertNotIn("private-error-canary", results[0].messages[0])
