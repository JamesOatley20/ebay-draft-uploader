import contextlib
import io
import logging
import os
import ssl
from unittest.mock import patch

from ebay_drafts import AppError
from ebay_drafts.auth import Auth, AuthExpired
from ebay_drafts.ebay import APIError
from ebay_drafts.network import silence_network_logging, tls_context
from support import BatchTest
import run


class AuthTests(BatchTest):
    def test_no_credential_storage_and_close(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.home / "localapp")}):
            auth = Auth("unique-private-token")
            self.assertEqual(auth.user_token(), "unique-private-token")
            self.assertNotIn("unique-private-token", repr(auth))
            auth.close()
            with self.assertRaises(AuthExpired):
                auth.user_token()
            with self.assertRaises(TypeError):
                Auth()
        self.assertFalse(self.storage.exists())

    def test_bad_token_does_not_echo(self):
        for token in ("", "Bearer private", "secret\nprivate"):
            with self.assertRaises(AppError) as caught:
                Auth(token)
            self.assertNotIn("private", str(caught.exception))

    def test_tls_key_logging_disabled_even_without_launcher(self):
        target = self.home / "keylog.txt"
        with patch.dict(os.environ, {"SSLKEYLOGFILE": str(target)}), patch("ssl.create_default_context", side_effect=AssertionError):
            context = tls_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertIsNone(context.keylog_filename)
        self.assertFalse(target.exists())

    def test_http_debug_handlers_cannot_capture_runtime(self):
        output = io.StringIO()
        logger = logging.getLogger("httpcore.connection")
        logger.addHandler(logging.StreamHandler(output))
        logger.setLevel(logging.DEBUG)
        silence_network_logging()
        logger.debug("private-canary")
        logging.getLogger("httpx").warning("private-canary")
        self.assertEqual(output.getvalue(), "")

    def test_entry_suppresses_unexpected_tracebacks_and_api_details(self):
        for error in (RuntimeError("private-canary"), APIError(400, "private-canary")):
            output = io.StringIO()
            with patch.object(run, "main", side_effect=error), contextlib.redirect_stderr(output):
                self.assertEqual(run.entry(), 2)
            self.assertNotIn("private-canary", output.getvalue())
            self.assertNotIn("Traceback", output.getvalue())

    def test_unknown_cli_arguments_not_echoed(self):
        output = io.StringIO()
        with patch("sys.argv", ["run.py", "--token", "private-canary"]), contextlib.redirect_stderr(output):
            self.assertEqual(run.entry(), 2)
        self.assertNotIn("private-canary", output.getvalue())
