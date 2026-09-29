"""Regression tests for the simple bulk-upload defaults added in 3.0.4."""

from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from ebay_drafts import AppError
from ebay_drafts.guards import GUARD_NAME, arm_guard
from ebay_drafts.notes import handoff_rows
from ebay_drafts.workflow import prepare_batch
from support import BatchTest, make_batch
import run


class BulkDefaultTests(BatchTest):
    def invoke(self, arguments=()):
        output = StringIO()
        with patch("sys.argv", ["run.py", "--batch", str(self.root), *arguments]), \
             patch("builtins.input", side_effect=AssertionError("normal batch upload must not ask console confirmations")), \
             patch("webbrowser.open"), \
             patch("ebay_drafts.migration.app_storage", return_value=self.storage), \
             patch("ebay_drafts.session_ui.run_session", return_value=[]) as session, redirect_stdout(output):
            result = run.main()
        return result, session, output.getvalue()

    def test_default_submits_every_ready_unguarded_item_without_console_ceremony(self):
        make_batch(self.root, ("Camera", "Lens"))
        code, session, text = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual([item.folder.name for item in session.call_args.args[0]], ["Camera", "Lens"])
        self.assertIn("Batch mode: all 2 ready", text)

    def test_optional_item_mode_still_allows_one_item_for_diagnostics(self):
        make_batch(self.root, ("Camera", "Lens"))
        code, session, _ = self.invoke(("--item", "Lens"))
        self.assertEqual(code, 0)
        self.assertEqual([item.folder.name for item in session.call_args.args[0]], ["Lens"])

    def test_guarded_item_is_skipped_but_does_not_force_folder_selection(self):
        make_batch(self.root, ("Camera", "Lens"))
        items, problems = prepare_batch(self.root)
        self.assertFalse(problems)
        arm_guard(items[0].output)
        code, session, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual([item.folder.name for item in session.call_args.args[0]], ["Lens"])
        self.assertTrue((items[0].output / GUARD_NAME).exists())

    def test_guarded_explicit_item_cannot_be_resubmitted(self):
        item = self.prepared()[0]
        arm_guard(item.output)
        with self.assertRaises(AppError):
            self.invoke(("--item", "Camera"))
        self.assertTrue((item.output / GUARD_NAME).exists())


class OfferGuidanceTests(BatchTest):
    def test_default_minimum_and_auto_accept_are_90_percent_of_asking_price(self):
        folder = self.root / "Camera"
        # Generated placeholders must not suppress the seller's standing 90% rule.
        (folder / "output.txt").write_text(
            "Best Offer minimum (GBP): Not provided — set in Seller Hub if wanted\n"
            "Best Offer auto-accept (GBP): Not provided — set in Seller Hub if wanted\n",
            encoding="utf-8",
        )
        item = self.prepared()[0]
        rows = {row.label: row for row in handoff_rows(item.listing, item.notes, item.research)}
        self.assertEqual(item.listing.price_gbp, Decimal("49.95"))
        self.assertEqual(rows["Best Offer minimum (GBP)"].value, "44.96")
        self.assertEqual(rows["Best Offer auto-accept (GBP)"].value, "44.96")
        self.assertIn("90%", rows["Best Offer minimum (GBP)"].source)

    def test_explicit_seller_offer_values_override_90_percent_default(self):
        folder = self.root / "Camera"
        (folder / "input.txt").write_text(
            "Best Offer minimum (GBP): 40.00\n"
            "Best Offer auto-accept (GBP): 45.00\n",
            encoding="utf-8",
        )
        item = self.prepared()[0]
        rows = {row.label: row for row in handoff_rows(item.listing, item.notes, item.research)}
        self.assertEqual(rows["Best Offer minimum (GBP)"].value, "40.00")
        self.assertEqual(rows["Best Offer auto-accept (GBP)"].value, "45.00")
