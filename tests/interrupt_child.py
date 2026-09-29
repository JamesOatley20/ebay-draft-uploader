"""A synthetic session which a parent test terminates at a chosen memory-only stage."""
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import httpx
from ebay_drafts.auth import Auth
from ebay_drafts.ebay import Ebay
from ebay_drafts.workflow import prepare_batch, submit_batch
from support import Service

options = json.loads(sys.stdin.readline())
service = Service(seed=options["seed"], outcome="pending" if options["stage"] == "pending" else "success")


def checkpoint(stage):
    if stage == options["stage"]:
        print(stage, flush=True)  # A fixed stage label, never a runtime value.
        while True:
            time.sleep(1)


class PausingEbay(Ebay):
    def upload_photo(self, photo):
        result = super().upload_photo(photo)
        checkpoint("photo")
        return result

    def create_task(self):
        result = super().create_task()
        checkpoint("task")
        return result

    def upload_draft(self, task, content):
        result = super().upload_draft(task, content)
        checkpoint("upload")
        return result

    def get_task(self, task):
        result = super().get_task(task)
        checkpoint("pending")
        return result

    def get_result(self, task):
        result = super().get_result(task)
        checkpoint("result")
        return result


items, problems = prepare_batch(Path(options["root"]))
assert not problems
with httpx.Client(transport=httpx.MockTransport(service.handle), trust_env=False) as client:
    api = PausingEbay(client, Auth(service.token), sleeper=lambda _: None)
    submit_batch(api, items, lambda event: checkpoint("completed") if event.status == "accepted" else None)
raise AssertionError("Checkpoint not reached")
