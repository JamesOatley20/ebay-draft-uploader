"""Small HTTP adapter with fixed eBay endpoints and conservative retry semantics."""

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit
import re
import time

import httpx

from . import AppError, SessionStopped
from .auth import Auth, AuthExpired
from .images import Photo

API_ROOT = "https://api.ebay.com"
MEDIA_ROOT = "https://apim.ebay.com"
FEED_PATH = "/sell/feed/v1/task"
MEDIA_PATH = "/commerce/media/v1_beta/image"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


class APIError(AppError):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.detail = message  # In-memory UI only. str(error) is safe for stderr.
        super().__init__("eBay could not complete this request. Check the session window and Seller Hub.")


class UncertainWrite(AppError):
    """The remote side may have processed a write; do not blindly retry it."""


def location_id(location: str, path_prefix: str) -> str:
    """Extract an ID only; never follow an arbitrary Location URL with credentials."""
    try:
        parsed = urlsplit(location)
    except ValueError as exc:
        raise AppError("eBay returned a malformed Location URL.") from exc
    if parsed.scheme != "https" or parsed.netloc not in {"api.ebay.com", "apim.ebay.com"}:
        raise AppError("eBay returned an unexpected Location host.")
    if parsed.query or parsed.fragment or not parsed.path.startswith(path_prefix + "/"):
        raise AppError("eBay returned an unexpected Location path.")
    identifier = parsed.path[len(path_prefix) + 1:]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", identifier):
        raise AppError("eBay returned an invalid resource identifier.")
    return identifier


def valid_image_url(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise AppError("eBay returned an invalid image URL.")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise AppError("eBay returned a malformed image URL.") from exc
    if (parsed.scheme != "https" or not parsed.hostname
            or not parsed.hostname.endswith(".ebayimg.com") or parsed.username
            or port not in {None, 443} or any(c in value for c in "\r\n|")):
        raise AppError("eBay image URL is not a trusted HTTPS eBay Picture Services URL.")
    return value


def cache_is_fresh(record: Any) -> bool:
    """Require at least a day of remaining EPS lifetime; missing expiry is not cached."""
    if not isinstance(record, dict):
        return False
    try:
        valid_image_url(record["url"])
        expiry = datetime.fromisoformat(record["expiration_date"].replace("Z", "+00:00"))
        return expiry.tzinfo is not None and expiry.timestamp() > time.time() + 86400
    except (AppError, KeyError, TypeError, ValueError, AttributeError):
        return False


class Ebay:
    """Upload pictures, create a draft task, and read its result."""

    def __init__(self, client: httpx.Client, auth: Auth, *, sleeper=time.sleep,
                 cancelled=lambda: False) -> None:
        self.client, self.auth, self.sleep = client, auth, sleeper
        self.cancelled = cancelled

    def check_cancelled(self) -> None:
        if self.cancelled():
            raise SessionStopped("Stopped locally. Remote work may continue; check Seller Hub before retrying.")

    def request(self, method: str, path: str, *, media: bool = False,
                **kwargs: Any) -> httpx.Response:
        """Retry safe reads only. No token refresh or replay of writes."""
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise AppError("Only fixed relative eBay endpoint paths are allowed.")
        root = MEDIA_ROOT if media else API_ROOT
        token_function = self.auth.user_token
        retries = 0
        while True:
            self.check_cancelled()
            headers = {"Authorization": "Bearer " + token_function(),
                       "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB", "Accept": "application/json"}
            try:
                with self.client.stream(method, root + path, headers=headers, **kwargs) as wire:
                    parts: list[bytes] = []
                    total = 0
                    for part in wire.iter_bytes():
                        self.check_cancelled()
                        total += len(part)
                        if total > MAX_RESPONSE_BYTES:
                            raise AppError("eBay response exceeds the 10 MB safety limit.")
                        parts.append(part)
                    # iter_bytes() already decodes HTTP Content-Encoding. Keeping that
                    # header would make a new Response decode the same payload twice.
                    decoded_headers = dict(wire.headers)
                    decoded_headers.pop("content-encoding", None)
                    decoded_headers.pop("content-length", None)
                    response = httpx.Response(wire.status_code, headers=decoded_headers,
                                              content=b"".join(parts), request=wire.request)
            except httpx.HTTPError as exc:
                if method != "GET":
                    raise UncertainWrite("Network failure during an eBay write. Its outcome is uncertain; do not blindly repeat it.") from exc
                if retries >= 2:
                    raise AppError("eBay read failed after three attempts.") from exc
                self.sleep(2 ** retries)
                retries += 1
                continue
            if response.status_code == 401:
                raise AuthExpired("The User token expired or was refused. No further items were submitted. Check Seller Hub before a new run.")
            if method == "GET" and response.status_code in {429, 500, 502, 503, 504} and retries < 2:
                retry_after = response.headers.get("Retry-After", "")
                delay = int(retry_after) if retry_after.isdigit() else 2 ** retries
                if delay > 30:
                    raise APIError(response.status_code, "eBay requested a longer retry delay; run again later.")
                self.sleep(max(1, delay))
                retries += 1
                continue
            if response.status_code >= 500 and method != "GET":
                raise UncertainWrite(f"eBay returned HTTP {response.status_code} during a write. The outcome is uncertain.")
            if not 200 <= response.status_code < 300:
                details = ""
                try:
                    payload = response.json()
                    errors = payload.get("errors", [])
                    if isinstance(errors, list):
                        details = "; ".join(
                            f"{e.get('errorId', '')}: {e.get('message', '')}" for e in errors[:5] if isinstance(e, dict)
                        )
                except (ValueError, AttributeError):
                    pass
                message = self.auth.redact(f"eBay HTTP {response.status_code}. {details}")[:1500]
                raise APIError(response.status_code, message)
            return response

    @staticmethod
    def json_body(response: httpx.Response) -> dict[str, Any]:
        try:
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError("Expected object")
            return value
        except ValueError as exc:
            raise AppError("eBay returned an invalid JSON object.") from exc

    def upload_photo(self, photo: Photo) -> dict[str, str | None]:
        """Use Media API multipart key 'image'; no deprecated Trading image upload."""
        response = self.request("POST", MEDIA_PATH + "/create_image_from_file", media=True,
                                files={"image": (photo.digest + ".jpg", photo.content, "image/jpeg")})
        payload = self.json_body(response) if response.content else {}
        if not payload.get("imageUrl"):
            image_id = location_id(response.headers.get("Location", ""), MEDIA_PATH)
            payload = self.json_body(self.request("GET", MEDIA_PATH + "/" + image_id, media=True))
        return {"url": valid_image_url(payload.get("imageUrl")),
                "expiration_date": payload.get("expirationDate")}

    def create_task(self) -> str:
        """Only the documented Seller Hub listing feed; never an Inventory offer."""
        response = self.request("POST", FEED_PATH,
                                json={"feedType": "FX_LISTING", "schemaVersion": "1.0"})
        return location_id(response.headers.get("Location", ""), FEED_PATH)

    def upload_draft(self, task_id: str, csv_content: bytes) -> None:
        from .feed import assert_draft_only
        assert_draft_only(csv_content)  # Last line of defence at the network boundary.
        self.request("POST", self._task_path(task_id) + "/upload_file",
                     files={"file": ("draft.csv", csv_content, "text/csv")})

    @staticmethod
    def _task_path(task_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", task_id):
            raise AppError("Invalid task ID in this session.")
        return FEED_PATH + "/" + task_id

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self.json_body(self.request("GET", self._task_path(task_id)))

    def get_result(self, task_id: str) -> bytes:
        return self.request("GET", self._task_path(task_id) + "/download_result_file").content
