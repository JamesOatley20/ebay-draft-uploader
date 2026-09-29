"""The documented Draft CSV fields, and eBay's per-item upload result."""

from dataclasses import dataclass
from html import escape
from io import BytesIO, StringIO
from xml.etree import ElementTree
import csv
import gzip
import re
import zipfile

from . import AppError
from .listing import Listing

# Keep the create/poll route together. Public eBay documentation still specifies
# FX_LISTING; FX_DRAFT has not been officially verified for EBAY_GB.
DRAFT_FEED_TYPE = "FX_LISTING"
DRAFT_SCHEMA_VERSION = "1.0"
MARKETPLACE = "EBAY_GB"
DRAFT_ROUTE_HELP = (
    "Draft task routing failed (BAF.Error.5). This does not identify a problem with "
    "the product description or price. The queue has stopped and the local guard remains. "
    "Resolve the prior task in Seller Hub Reports, then ask eBay Developer Support "
    "to confirm the draft feed type/schema for EBAY_GB and compare a fresh UK draft "
    "template. FX_DRAFT is unverified here. Do not switch to Add or blindly retry."
)

ACTION = "Action(SiteID=UK|Country=GB|Currency=GBP|CC=UTF-8)"
HEADERS = [ACTION, "Custom label (SKU)", "Category ID", "Title", "Condition ID",
           "Item photo URL", "Description", "Format", "Quantity", "Start price"]
MAX_RESULT_BYTES = 8 * 1024 * 1024
csv.field_size_limit(1_000_000)


def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def make_preparation_csv(listing: Listing, sku: str) -> bytes:
    """The only CSV allowed on disk: local fields, with an empty photo URL cell."""
    return make_upload_csv(listing, [], sku)


def is_preparation_csv(content: bytes) -> bool:
    try:
        assert_draft_only(content)
        rows = list(csv.reader(StringIO(content.decode("utf-8-sig"))))
        return rows[1][5] == ""
    except (AppError, UnicodeError, csv.Error, ValueError, IndexError):
        return False


def make_upload_csv(listing: Listing, image_urls: list[str], sku: str) -> bytes:
    """Transmit these bytes directly; never pass them to a filesystem writer."""
    photos = "|".join(image_urls)
    if len(photos) > 2048:
        raise AppError("The combined photo links exceed eBay's draft field limit.")
    description = "<p>" + escape(listing.description) + "</p>"
    if len(description) > 32765:
        raise AppError("The description is too long after HTML escaping.")
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(HEADERS)
    writer.writerow(["Draft", sku, listing.category_id, listing.title,
                     listing.condition_id if listing.condition_id is not None else "",
                     photos, description, "FixedPrice", listing.quantity,
                     f"{listing.price_gbp:.2f}" if listing.price_gbp is not None else ""])
    content = output.getvalue().encode("utf-8-sig")
    assert_draft_only(content)
    return content


def assert_draft_only(content: bytes) -> None:
    """Check again immediately before sending: this app cannot publish a listing."""
    try:
        rows = list(csv.reader(StringIO(content.decode("utf-8-sig"))))
        if (len(rows) != 2 or rows[0] != HEADERS or len(rows[1]) != len(HEADERS)
                or rows[1][0] != "Draft" or rows[1][7] != "FixedPrice"):
            raise AppError("Upload stopped: this is not a single fixed-price Draft row.")
    except (UnicodeError, csv.Error) as error:
        raise AppError("Upload stopped: the draft file is unreadable.") from error


@dataclass(frozen=True)
class Result:
    status: str  # success | rejected | unknown
    messages: list[str]


def unpack_result(content: bytes) -> bytes:
    """Bounded gzip/zip decompression without writing archive members to disk."""
    try:
        if content.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=BytesIO(content)) as archive:
                result = archive.read(MAX_RESULT_BYTES + 1)
        elif content.startswith(b"PK\x03\x04"):
            with zipfile.ZipFile(BytesIO(content)) as archive:
                members = [m for m in archive.infolist() if not m.is_dir()]
                if len(members) != 1 or members[0].file_size > MAX_RESULT_BYTES:
                    raise AppError("Result archive must contain one small report.")
                with archive.open(members[0]) as stream:
                    result = stream.read(MAX_RESULT_BYTES + 1)
        else:
            result = content
    except (OSError, EOFError, zipfile.BadZipFile, RuntimeError) as exc:
        raise AppError("eBay result archive is malformed or unsupported.") from exc
    if len(result) > MAX_RESULT_BYTES:
        raise AppError("Decompressed result exceeds the 8 MB limit.")
    return result


def parse_result(content: bytes) -> Result:
    """Require explicit row-level success. HTTP 200 / task COMPLETED is not enough."""
    try:
        payload = unpack_result(content)
        try:
            value = payload.decode("utf-8-sig").strip()
        except UnicodeDecodeError:
            value = payload.decode("cp1252").strip()
        if not value:
            return Result("unknown", ["Empty result file."])
        result = _xml_result(value) if value.startswith("<") else _csv_result(value)
        if ("baf.error.5" in value.lower()
                or "unable to find task action id for task draft" in value.lower()):
            return Result("rejected", [*result.messages, DRAFT_ROUTE_HELP])
        return result
    except (AppError, UnicodeError, csv.Error, ElementTree.ParseError, ValueError) as exc:
        return Result("unknown", [f"Could not safely interpret the result: {exc}"])


def _csv_result(value: str) -> Result:
    rows = list(csv.reader(StringIO(value)))
    header_index = next((i for i, row in enumerate(rows) if "status" in {normalise(c) for c in row}), None)
    if header_index is None:
        return Result("unknown", ["No recognised Status column in result; check Seller Hub Reports."])
    headers = [normalise(c) for c in rows[header_index]]
    data_rows = [row for row in rows[header_index + 1:] if any(c.strip() for c in row)]
    if len(data_rows) != 1 or len(data_rows[0]) != len(headers) or len(set(headers)) != len(headers):
        return Result("unknown", ["Expected one unambiguous result row for the one-listing task."])
    record = dict(zip(headers, data_rows[0]))
    status = record.get("status", "").strip().lower()
    messages = [f"{key}: {val}" for key, val in record.items() if val and ("message" in key or "code" in key)]
    errors = [v for k, v in record.items() if k.startswith("errorcode") and v.strip() not in {"", "0"}]
    if status in {"failure", "failed", "error"} or errors:
        return Result("rejected", messages or ["eBay rejected the draft row."])
    if status in {"success", "warning"}:
        return Result("success", messages)
    return Result("unknown", messages or [f"Unrecognised result status: {status}."])


def _xml_result(value: str) -> Result:
    if "<!DOCTYPE" in value.upper() or "<!ENTITY" in value.upper():
        raise AppError("XML document types and entities are prohibited.")
    root = ElementTree.fromstring(value)
    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]
    responses = [e for e in root.iter() if local(e.tag) == "VerifyAddItemResponse"]
    if len(responses) != 1:
        return Result("unknown", ["Expected one VerifyAddItemResponse for the draft row; check Seller Hub Reports."])
    root = responses[0]
    acknowledgements = [e.text.strip().lower() for e in root.iter()
                        if local(e.tag) == "Ack" and e.text]
    messages: list[str] = []
    fatal = False
    for node in root.iter():
        if local(node.tag) == "Errors":
            details = {local(e.tag): e.text or "" for e in node}
            messages.append(": ".join(filter(None, (details.get("ErrorCode"), details.get("LongMessage") or details.get("ShortMessage")))))
            if details.get("SeverityCode", "Error").lower() == "error":
                fatal = True
    if fatal or any(ack in {"failure", "partialfailure"} for ack in acknowledgements):
        return Result("rejected", messages or ["eBay rejected the draft."])
    if len(acknowledgements) == 1 and acknowledgements[0] in {"success", "warning"}:
        return Result("success", messages)
    return Result("unknown", messages or ["XML result did not contain exactly one explicit successful acknowledgement."])
