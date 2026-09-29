"""Synthetic regression coverage, NOT a captured official template or live API proof."""
from contextlib import redirect_stdout
from io import StringIO
import csv
import json
from unittest.mock import patch

import httpx

from ebay_drafts import AppError
from ebay_drafts.feed import DRAFT_FEED_TYPE, DRAFT_SCHEMA_VERSION, HEADERS, make_upload_csv, parse_result
from ebay_drafts.guards import GUARD_NAME, arm_guard
from ebay_drafts.listing import Listing
from ebay_drafts.notes import handoff_rows
from ebay_drafts.template_check import compare_template
from ebay_drafts.workflow import check_reviewed_files, prepare_batch, submit_batch
from support import BatchTest, LISTING, Service, make_batch
import run


# Independent literal pins the existing serializer. Not labelled as an eBay download.
HEADER = ('Action(SiteID=UK|Country=GB|Currency=GBP|CC=UTF-8),Custom label (SKU),'
          'Category ID,Title,Condition ID,Item photo URL,Description,Format,Quantity,Start price')


class HandoffTests(BatchTest):
    def test_missing_input_continues_without_inventing_measurements_or_working_claim(self):
        path = self.root / "Camera" / "input.txt"
        path.unlink()
        item = self.prepared()[0]
        self.assertIsNone(item.notes.dimensions)
        self.assertIsNone(item.notes.weight)
        self.assertNotIn("fully working", item.notes.condition)
        self.assertFalse(path.exists())
        self.assertIsNone(item.input_hashes["input.txt"])
        check_reviewed_files(item)
        self.assertIn("input.txt is missing", (item.output.parent / "preview.html").read_text())

    def test_empty_input_does_not_assert_working_order(self):
        (self.root / "Camera" / "input.txt").write_text("", encoding="utf-8")
        item = self.prepared()[0]
        self.assertIn("Not provided", item.notes.condition)
        self.assertNotIn("fully working", item.notes.condition)

    def test_added_missing_input_is_a_review_change_and_sends_nothing(self):
        path = self.root / "Camera" / "input.txt"
        path.unlink()
        item = self.prepared()[0]
        path.write_text("New notes", encoding="utf-8")
        service = Service()
        with service.api() as api:
            self.assertEqual(submit_batch(api, [item])[0].status, "needs_review")
        self.assertFalse(service.calls)
        self.assertFalse((item.output / GUARD_NAME).exists())

    def test_changed_output_is_a_review_change(self):
        item = self.prepared()[0]
        with (item.folder / "output.txt").open("a", encoding="utf-8") as stream:
            stream.write("Changed price guidance")
        with self.assertRaises(AppError):
            check_reviewed_files(item)

    def test_explicit_manual_values_override_research_not_listing(self):
        folder = self.root / "Camera"
        (folder / "input.txt").write_text(
            "Best Offer minimum (GBP): 40.00\nBest Offer auto-accept (GBP): 45.00\n"
            "Postage service: Tracked service selected by seller\n"
            "Postage charged to buyer (GBP): 5.25\nPackage dimensions (cm): 20 x 15 x 10\n"
            "Package weight (kg): 1.2\n", encoding="utf-8")
        (folder / "output.txt").write_text(
            "Best Offer minimum (GBP): 30.00\nPrice guidance (GBP): 60.00\n", encoding="utf-8")
        item = self.prepared()[0]
        rows = {row.label: row for row in handoff_rows(item.listing, item.notes, item.research)}
        self.assertEqual(rows["Best Offer minimum (GBP)"].value, "40.00")
        self.assertEqual(rows["Best Offer auto-accept (GBP)"].value, "45.00")
        self.assertEqual(rows["Asking price (GBP)"].value, "49.95")
        self.assertEqual(rows["Price guidance (GBP)"].value, "60.00")
        self.assertIn("input.txt", rows["Best Offer minimum (GBP)"].source)
        preview = (item.output.parent / "preview.html").read_text()
        for value in ("45.00", "5.25", "20 x 15 x 10", "1.2", "NOT SENT", "Start price"):
            self.assertIn(value, preview)
        wire = make_upload_csv(item.listing, [], "local-test")
        self.assertNotIn(b"Tracked service", wire)
        self.assertNotIn(b"Best Offer", wire)
        self.assertEqual(json.loads((folder / "listing.json").read_text()), LISTING)

    def test_old_free_form_notes_are_visible_and_html_escaped(self):
        path = self.root / "Camera" / "output.txt"
        authored = 'Private estimate: £77.00; offers over £63.50. <script>alert(1)</script>\n'
        path.write_text(authored, encoding="utf-8")
        item = self.prepared()[0]
        preview = (item.output.parent / "preview.html").read_text()
        self.assertIn("offers over £63.50", preview)
        self.assertIn("&lt;script&gt;", preview)
        self.assertNotIn("<script>", preview)
        self.assertTrue(path.read_text().startswith(authored))
        self.assertNotIn("Optional Best Offer suggestions", path.read_text())

    def test_conflicting_manual_labels_are_not_silently_overwritten(self):
        (self.root / "Camera" / "input.txt").write_text(
            "Best Offer minimum (GBP): 30.00\nBest Offer minimum (GBP): 40.00\n", encoding="utf-8")
        item = self.prepared()[0]
        row = next(r for r in handoff_rows(item.listing, item.notes) if r.label == "Best Offer minimum (GBP)")
        self.assertEqual(row.value, "CONFLICT — 30.00 / 40.00")

    def test_invalid_existing_input_is_not_treated_as_missing(self):
        (self.root / "Camera" / "input.txt").write_bytes(b"\xff\xfeinvalid")
        items, problems = prepare_batch(self.root)
        self.assertFalse(items)
        self.assertIn("UTF-8", problems["Camera"])


class TemplateTests(BatchTest):
    def test_existing_serializer_has_exact_header_bom_crlf_and_one_draft(self):
        wire = make_upload_csv(Listing.parse(LISTING), [], "local-test")
        self.assertTrue(wire.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(wire.endswith(b"\r\n"))
        rows = list(csv.reader(StringIO(wire.decode("utf-8-sig"))))
        self.assertEqual(rows[0], next(csv.reader([HEADER])))
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[1][0], rows[1][7], rows[1][9]), ("Draft", "FixedPrice", "49.95"))

    def test_identical_blank_layout_not_claimed_live_compatible(self):
        report = compare_template((HEADER + "\r\n").encode("utf-8-sig"))
        self.assertFalse(report.different)
        self.assertIn("This is not API compatibility proof", "\n".join(report.lines))

    def test_metadata_bom_and_optional_column_differences_are_reported(self):
        # Deliberately synthetic; a fresh UK template still needs to be obtained.
        data = ('#INFO,synthetic-metadata,,\r\n*' + HEADER + ',UPC,Buy It Now price\r\n').encode()
        report = compare_template(data)
        self.assertTrue(report.different)
        text = "\n".join(report.lines)
        self.assertIn("without BOM", text)
        self.assertIn("Metadata rows: 1", text)
        self.assertIn("header CSV record: 2", text)
        self.assertIn("UPC, Buy It Now price", text)
        self.assertNotIn("synthetic-metadata", text)

    def test_wrong_marketplace_data_rows_results_and_add_are_rejected(self):
        samples = [HEADER.replace("SiteID=UK", "SiteID=US"),
                   HEADER + "\nAdd,,,,,,,,,\n", HEADER + "\nDraft,,31388,Camera,,,,,,\n",
                   "Status,Message\nFailure,private-result\n", HEADER + ",Shipping service 1 cost\n"]
        for data in samples:
            with self.subTest(data=data[:40]), self.assertRaises(AppError):
                compare_template(data.encode())

    def test_duplicate_or_missing_category_column_rejected(self):
        for data in (HEADER.replace("Category ID", "Category"), HEADER + ",Title"):
            with self.assertRaises(AppError):
                compare_template(data.encode())


class RoutingTests(BatchTest):
    def test_create_request_remains_documented_route_and_multipart_contract(self):
        service = Service()
        original = service.handle
        seen = []
        def handler(request):
            if request.method == "POST" and request.url.path.endswith("/task"):
                self.assertEqual(json.loads(request.read()),
                                 {"feedType": DRAFT_FEED_TYPE, "schemaVersion": DRAFT_SCHEMA_VERSION})
                self.assertEqual(request.headers["X-EBAY-C-MARKETPLACE-ID"], "EBAY_GB")
                seen.append(True)
            return original(request)
        service.handle = handler
        with service.api() as api:
            submit_batch(api, self.prepared())
        self.assertEqual(seen, [True])
        self.assertIn(b'name="file"; filename="draft.csv"', service.upload)
        self.assertNotIn(b"FX_DRAFT", service.upload)
        self.assert_no_runtime(service.prohibited)

    def test_routing_code_cannot_be_misreported_as_success(self):
        for payload in (b"BAF.Error.5 Unable to find Task Action Id for task Draft",
                        b"Status,Message\nSuccess,BAF.Error.5\n"):
            result = parse_result(payload)
            self.assertEqual(result.status, "rejected")
            self.assertIn("Do not switch to Add", "\n".join(result.messages))

    def test_missing_identity_wrong_feed_and_partial_state_stop_queue(self):
        make_batch(self.root, ("Camera", "Lens"))
        for replacement in ({"feedType": "FX_DRAFT"}, {"taskId": None}, {"feedType": None},
                            {"status": "PARTIALLY_PROCESSED"}, {"status": "NEW_UNKNOWN_STATE"}):
            items = self.prepared()
            service = Service()
            original = service.handle
            def handler(request):
                response = original(request)
                if request.method == "GET" and request.url.path.endswith(service.task):
                    return httpx.Response(200, json={**response.json(), **replacement})
                return response
            service.handle = handler
            with service.api() as api:
                result = submit_batch(api, items)
            self.assertEqual([r.status for r in result], ["needs_review", "not_attempted"])
            self.assert_no_runtime(service.prohibited)
            from ebay_drafts.guards import release_guard
            release_guard(items[0].output)


class SelectionTests(BatchTest):
    def invoke(self, arguments, answers):
        output = StringIO()
        with patch("sys.argv", ["run.py", "--batch", str(self.root), *arguments]), \
             patch("builtins.input", side_effect=answers), patch("webbrowser.open"), \
             patch("ebay_drafts.migration.app_storage", return_value=self.storage), \
             patch("ebay_drafts.session_ui.run_session", return_value=[]) as session, redirect_stdout(output):
            result = run.main()
        return result, session, output.getvalue()

    def test_explicit_item_submits_only_the_chosen_item(self):
        make_batch(self.root, ("Camera", "Lens"))
        code, session, _ = self.invoke(["--item", "Lens"], ["RESOLVED", "DRAFT"])
        self.assertEqual(code, 0)
        self.assertEqual([i.folder.name for i in session.call_args.args[0]], ["Lens"])

    def test_interactive_selection_does_not_default_to_whole_batch(self):
        make_batch(self.root, ("Camera", "Lens"))
        _, session, _ = self.invoke([], ["Lens", "RESOLVED", "DRAFT"])
        self.assertEqual([i.folder.name for i in session.call_args.args[0]], ["Lens"])

    def test_unresolved_prior_work_cancels_before_authentication(self):
        _, session, _ = self.invoke(["--item", "Camera"], [""])
        session.assert_not_called()
        self.assertFalse(list(self.root.rglob(GUARD_NAME)))

    def test_selection_never_releases_a_guard(self):
        item = self.prepared()[0]
        arm_guard(item.output)
        with self.assertRaises(AppError):
            self.invoke(["--item", "Camera"], [])
        self.assertTrue((item.output / GUARD_NAME).exists())
