"""Offline comparison with a seller-downloaded UK draft template.

This does not download, modify, adopt or upload a template. In particular it does
not guess that metadata or an encoding change will fix a server routing error.
"""

from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
import codecs
import csv
import re

from . import AppError
from .feed import ACTION, HEADERS

# These are the optional draft columns in eBay's draft-field guide, not Add fields.
DRAFT_COLUMNS = set(HEADERS[1:]) | {"UPC", "Buy It Now price"}


@dataclass(frozen=True)
class TemplateComparison:
    lines: list[str]
    different: bool


def compare_template(content: bytes) -> TemplateComparison:
    """Accept a blank UK CSV only, so result reports or seller rows aren't printed."""
    if not content or len(content) > 256_000:
        raise AppError("Select a blank draft CSV template no larger than 256 KB.")
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.reader(StringIO(text, newline=""), strict=True))
    except (UnicodeError, csv.Error):
        raise AppError("The selected template is not a readable UTF-8 CSV. No upload was made.") from None
    if len(rows) > 1000 or any(len(row) > 50 for row in rows):
        raise AppError("The selected file is too large to be a simple blank draft template.")
    candidates = [(index, row) for index, row in enumerate(rows)
                  if row and row[0].lstrip("*").startswith("Action(")]
    if len(candidates) != 1:
        raise AppError("Expected exactly one Action(...) header in a blank draft template, not a result report.")
    header_index, headers = candidates[0]
    action = headers[0].lstrip("*")
    match = re.fullmatch(r"Action\(([^()]*)\)", action)
    if not match:
        raise AppError("The draft template's Action header is not recognised.")
    parameters = {}
    for cell in match[1].split("|"):
        name, separator, value = cell.partition("=")
        if not separator or name in parameters:
            raise AppError("The draft template has ambiguous Action parameters.")
        parameters[name] = value
    if any(parameters.get(k) != v for k, v in
           {"SiteID": "UK", "Country": "GB", "Currency": "GBP", "CC": "UTF-8"}.items()):
        raise AppError("Use a UK / GB / GBP / UTF-8 draft template downloaded from the UK seller account.")
    names = [name.lstrip("*") for name in headers[1:]]
    if len(set(names)) != len(names) or not names or "Category ID" not in names:
        raise AppError("The template has duplicate columns or lacks Category ID.")
    if set(names) - DRAFT_COLUMNS:
        raise AppError("This template contains fields outside the documented draft-field guide; review it with eBay Support.")
    metadata = []
    for index, row in enumerate(rows):
        if index == header_index or not any(cell.strip() for cell in row):
            continue
        if row[0] == "#INFO":
            metadata.append((index + 1, row))
        elif index > header_index and len(row) == len(headers) and row[0] in {"", "Draft"} and not any(row[1:]):
            continue  # An empty Draft placeholder is not an item to submit.
        else:
            raise AppError("Select a blank template: populated rows or non-Draft actions are not accepted.")
    bom = content.startswith(codecs.BOM_UTF8)
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    missing = [name for name in HEADERS[1:] if name not in names]
    optional = [name for name in names if name not in HEADERS[1:]]
    different = headers != HEADERS or bool(metadata) or not bom or bool(lf or cr) or not text.endswith("\r\n")
    lines = [
        "OFFLINE COMPARISON ONLY — no API request; no template has been adopted.",
        "Provenance cannot be verified by this command. Download fresh from Seller Hub UK.",
        "Template SHA-256: " + sha256(content).hexdigest(),
        "App serializer: UTF-8 with BOM; CRLF; header + one Draft/FixedPrice row; no #INFO rows.",
        f"Selected template: UTF-8 {'with' if bom else 'without'} BOM; CRLF={crlf}, lone LF={lf}, lone CR={cr}.",
        f"Final CRLF: {text.endswith(chr(13) + chr(10))}; header CSV record: {header_index + 1}.",
        "App Action header: " + ACTION,
        "Template Action header: " + headers[0],
        "App columns: " + " | ".join(HEADERS[1:]),
        "Template columns: " + " | ".join(headers[1:]),
        "Missing app columns: " + (", ".join(missing) or "none"),
        "Additional documented optional columns: " + (", ".join(optional) or "none"),
        f"Metadata rows: {len(metadata)}. The app currently emits none.",
    ]
    for number, row in metadata:
        # Structural fingerprints compare metadata without echoing arbitrary text.
        digest = sha256("\x1f".join(row).encode("utf-8")).hexdigest()
        lines.append(f"#INFO at CSV record {number}: {len(row)} cells; content SHA-256 {digest}.")
    lines += ["Differences found: " + ("YES — review before a live test." if different else "NO structural differences found."),
              "This is not API compatibility proof. Buy It Now price is not used for FixedPrice; Start price is.",
              "Do not change to Add or infer FX_DRAFT support from this comparison."]
    return TemplateComparison(lines, different)
