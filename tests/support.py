from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
import json
import tempfile
import unittest
import uuid

import httpx
from PIL import Image

from ebay_drafts.auth import Auth
from ebay_drafts.ebay import Ebay
from ebay_drafts.workflow import prepare_batch

LISTING = {
    "title": "Seller's camera",
    "category_id": "31388",
    "price_gbp": "49.95",
    "condition_id": 3000,
    "description": "My camera in good used condition, with its strap.",
    "quantity": 1,
}


def make_batch(root, names=("Camera",), version=3):
    root.mkdir(parents=True, exist_ok=True)
    (root / "batch.json").write_text(json.dumps({"version": version, "items": list(names), "skipped": {}}), encoding="utf-8")
    for name in names:
        folder = root / name
        folder.mkdir(exist_ok=True)
        (folder / "listing.json").write_text(json.dumps(LISTING), encoding="utf-8")
        (folder / "input.txt").write_text("Condition: Good\nPackage dimensions (cm): 20 x 15 x 10\nPackage weight (kg): 1\n", encoding="utf-8")
        (folder / "output.txt").write_text("Seller notes and research: https://www.ebay.co.uk/itm/123456\nChosen price £49.95.\n\n", encoding="utf-8")
        output = BytesIO()
        Image.new("RGB", (600, 500), "navy").save(output, "JPEG")
        (folder / "photo.jpg").write_bytes(output.getvalue())


class Service:
    def __init__(self, seed=None, outcome="success"):
        self.seed = seed or uuid.uuid4().hex
        self.token = "oauth-" + self.seed
        self.task = "task-" + self.seed
        self.url = "https://i.ebayimg.com/images/" + self.seed + "/photo.jpg"
        self.expiry = "2099-12-31T12:34:56Z"
        self.message = "user-" + self.seed
        self.outcome = outcome
        self.calls = []
        self.upload = b""
        self.on_photo = lambda: None
        self.on_poll = lambda: None

    def handle(self, request):
        self.calls.append((request.method, request.url.path))
        if request.headers["Authorization"] != "Bearer " + self.token:
            return httpx.Response(401)
        path = request.url.path
        if path.endswith("/create_image_from_file"):
            self.on_photo()
            if self.outcome == "photo-error":
                return httpx.Response(400, json={"errors": [{"errorId": "123", "message": self.message + self.token}]})
            return httpx.Response(201, json={"imageUrl": self.url, "expirationDate": self.expiry, "userId": self.message})
        if path.endswith("/upload_file"):
            self.upload = request.read()
            if self.outcome == "upload-timeout":
                raise httpx.ReadTimeout(self.token, request=request)
            if self.outcome == "401":
                return httpx.Response(401, json={"message": self.token})
            return httpx.Response(200)
        if path.endswith("/download_result_file"):
            if self.outcome == "malformed":
                return httpx.Response(200, content=b"unrecognised-" + self.message.encode())
            if self.outcome == "feed-rejected":
                return httpx.Response(200, content=(
                    "Status,ErrorCode,ErrorMessage,Message\r\n"
                    "Failure,BAF.Error.5,Unable to find Task Action Id for task Draft,"
                    + self.message + self.token + "\r\n").encode())
            result = "Failure" if self.outcome == "rejected" else "Success"
            return httpx.Response(200, content=f"Status,Message\n{result},{self.message}\n".encode())
        if request.method == "POST" and path.endswith("/task"):
            return httpx.Response(202, headers={"Location": "https://api.ebay.com/sell/feed/v1/task/" + self.task})
        if request.method == "GET":
            self.on_poll()
            return httpx.Response(200, json={"taskId": self.task, "feedType": "FX_LISTING",
                                           "status": "IN_PROCESS" if self.outcome == "pending" else "COMPLETED",
                                           "userId": self.message})
        raise AssertionError("Unexpected synthetic request")

    @contextmanager
    def api(self, **kwargs):
        auth = Auth(self.token)
        with httpx.Client(transport=httpx.MockTransport(self.handle), trust_env=False) as client:
            yield Ebay(client, auth, sleeper=kwargs.pop("sleeper", lambda _: None), **kwargs)
        auth.close()

    @property
    def prohibited(self):
        return [self.token, self.task, self.url, self.expiry, self.message]


class BatchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ebay-drafts-test-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "batch"
        self.storage = self.home / "localapp" / "eBayDrafts"
        make_batch(self.root)

    def prepared(self):
        items, problems = prepare_batch(self.root)
        self.assertFalse(problems)
        return items

    def assert_no_runtime(self, values):
        for path in self.home.rglob("*"):
            if path.is_file():
                data = path.read_bytes()
                for value in values:
                    self.assertNotIn(value.encode(), data, str(path))
                    self.assertNotIn(value.encode("utf-16-le"), data, str(path))
