from io import StringIO
import csv
import gzip
import json
import zipfile
from io import BytesIO
from pathlib import Path

from ebay_drafts import AppError
from ebay_drafts.feed import make_preparation_csv, make_upload_csv, is_preparation_csv, assert_draft_only, parse_result
from ebay_drafts.listing import Listing
from support import BatchTest, LISTING


class ContractTests(BatchTest):
    def test_overlay_launcher_matches_installed_launcher(self):
        root = Path(__file__).resolve().parents[1]
        guide = (root / "chatgpt" / "03-Build-Overlay.md").read_text(encoding="utf-8")
        template = guide.split("```bat\n", 1)[1].split("```", 1)[0].strip()
        launcher = (root / "Open-eBay-Drafts.cmd").read_text(encoding="utf-8").strip()
        self.assertEqual(template, launcher)
        self.assertIn('"version": 3', guide)

    def test_six_field_listing_and_disk_csv_preserve_preparation(self):
        item = self.prepared()[0]
        content = (item.output / "draft.csv").read_bytes()
        rows = list(csv.reader(StringIO(content.decode("utf-8-sig"))))
        self.assertTrue(is_preparation_csv(content))
        self.assertEqual(rows[1][5], "")
        self.assertEqual(rows[1][2], LISTING["category_id"])
        self.assertEqual(rows[1][4], str(LISTING["condition_id"]))
        self.assertEqual(rows[1][9], LISTING["price_gbp"])
        self.assertEqual(json.loads((item.folder / "listing.json").read_text()), LISTING)
        report = (item.folder / "output.txt").read_text(encoding="utf-8")
        self.assertIn("https://www.ebay.co.uk/itm/123456", report)
        self.assertIn("Chosen price £49.95", report)
        self.assertIn("LOCAL PREPARATION", report)
        self.assertNotIn("APP STATUS", report)

    def test_only_transmitted_csv_has_runtime_photo_urls(self):
        listing = Listing.parse(LISTING)
        local = make_preparation_csv(listing, "local-sku")
        uploaded = make_upload_csv(listing, ["https://i.ebayimg.com/runtime"], "local-sku")
        self.assertNotIn(b"/runtime", local)
        self.assertIn(b"/runtime", uploaded)
        self.assertFalse(is_preparation_csv(uploaded))
        assert_draft_only(uploaded)
        with self.assertRaises(AppError):
            assert_draft_only(uploaded.replace(b"Draft,", b"Add,"))

    def test_result_archives_remain_memory_only(self):
        raw = b"Status,Message\nSuccess,synthetic-user-record\n"
        zipped = BytesIO()
        with zipfile.ZipFile(zipped, "w") as archive:
            archive.writestr("result.csv", raw)
        for payload in (raw, gzip.compress(raw), zipped.getvalue()):
            result = parse_result(payload)
            self.assertEqual(result.status, "success")
            self.assertIn("synthetic-user-record", result.messages[0])
        self.assertFalse(list(self.root.rglob("result*")))

    def test_account_fields_not_accepted_as_listing_fields(self):
        with self.assertRaises(AppError):
            Listing.parse({**LISTING, "task_id": "not-a-listing-field"})
