"""Read the seller's notes and keep private information out of the advert."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from .files import check_path, read_text, write_text
from .listing import Listing

DEFAULT_CONDITION = "Not provided. Confirm the item's condition before publishing."
STATUS_MARKER = "=== APP STATUS (replaced on each run) ==="
PREPARATION_MARKER = "=== LOCAL PREPARATION (replaced on each run) ==="


def section_start(content: bytes, marker: str) -> int | None:
    found = re.search(rb"(?m)^" + re.escape(marker.encode("utf-8")) + rb"\r?$", content)
    return found.start() if found else None


def authored_prefix(content: bytes) -> bytes:
    """Preserve every authored byte before either recognised app-owned section."""
    positions = []
    for marker in (STATUS_MARKER, PREPARATION_MARKER):
        start = section_start(content, marker)
        if start is not None:
            positions.append(start)
    return content[:min(positions)] if positions else content


@dataclass(frozen=True)
class SellerNotes:
    original: str
    condition: str
    dimensions: tuple[Decimal, ...] | None
    weight: Decimal | None
    missing: list[str]

    @classmethod
    def read(cls, folder: Path) -> "SellerNotes":
        path = folder / "input.txt"
        check_path(path)  # A missing file is allowed; a link or unreadable file is not.
        if path.exists():
            return cls.parse(read_text(path, 32_000))
        return cls.parse("", missing_file=True)

    @classmethod
    def parse(cls, original: str, *, missing_file: bool = False) -> "SellerNotes":
        values = {}
        for line in original.splitlines():
            name, separator, value = line.partition(":")
            if separator:
                values[name.strip().casefold()] = value.strip()
        dimensions = None
        weight = None
        missing = []
        size_text = values.get("package dimensions (cm)", "")
        weight_text = values.get("package weight (kg)", "")
        try:
            parts = re.split(r"\s*[x×*]\s*", re.sub(r"\s*cm\s*$", "", size_text, flags=re.I))
            if len(parts) != 3:
                raise ValueError
            dimensions = tuple(Decimal(p.strip()) for p in parts)
            if any(not n.is_finite() or not 0 < n <= 100000 for n in dimensions):
                raise ValueError
        except (ValueError, InvalidOperation):
            dimensions = None
            missing.append("Packed dimensions are missing or unclear. Measure the parcel in cm before arranging postage.")
        try:
            weight = Decimal(re.sub(r"\s*kg\s*$", "", weight_text, flags=re.I))
            if not weight.is_finite() or not 0 < weight <= 100000:
                raise ValueError
        except (ValueError, InvalidOperation):
            weight = None
            missing.append("Packed weight is missing or unclear. Weigh the parcel in kg before arranging postage.")
        condition = values.get("condition") or DEFAULT_CONDITION
        if missing_file:
            condition = "Not provided. Confirm the item's condition before publishing."
            missing.insert(0, "input.txt is missing; preparation continued without seller notes.")
        return cls(original, condition, dimensions, weight, missing)


def update_preparation(folder: Path, messages: list[str],
                  listing: Listing | None = None, notes: SellerNotes | None = None) -> None:
    """Called only before authentication, with local preparation information."""
    path = folder / "output.txt"
    existing = read_text(path, 256_000) if path.exists() else ""
    private_notes = authored_prefix(existing.encode("utf-8")).decode("utf-8")
    lines = [PREPARATION_MARKER, "Local preparation only. This file does not record upload outcomes.", *messages]
    if listing and notes:
        lines += ["", "FIELD HANDOFF — planned values, NOT an upload result"]
        for row in handoff_rows(listing, notes, private_notes):
            lines.append(f"{row.label}: {row.value} | {row.destination} | Source: {row.source}")
        lines.append("No offer thresholds are calculated or enabled automatically.")
    if listing:
        lines += ["", f"Title: {listing.title}", f"Category ID: {listing.category_id}"]
        if listing.price_gbp is None:
            lines.append("Price: MISSING. Set your asking price in Seller Hub before publishing.")
        else:
            lines.append(f"Asking price: GBP {listing.price_gbp:.2f} (sent as Start price, not Buy It Now price).")
        if listing.condition_id is None:
            lines.append("Condition code: not sent. Select the category's correct used/good condition in Seller Hub, unless your notes say otherwise.")
        else:
            lines.append(f"Condition ID supplied: {listing.condition_id}. Review its meaning for this category on eBay.")
        lines += ["", "BUYER DESCRIPTION", listing.description]
    if notes:
        lines += ["", "SELLER NOTES (not uploaded as separate fields)",
                  "Condition used for preparation: " + notes.condition, notes.original.rstrip()]
        if notes.dimensions:
            lines.append("Packed dimensions: " + " x ".join(map(str, notes.dimensions)) + " cm.")
        if notes.weight:
            lines.append(f"Packed weight: {notes.weight} kg.")
        lines += ["", *notes.missing]
    lines += ["", "FINISH ON EBAY", "Review the photos, description, category, condition and asking price.",
              "Complete item specifics, delivery/collection, parcel details, dispatch time, location and account policies as applicable.",
              "Separate condition notes and Best Offer settings are not sent by this app.",
              "Only title, category, price (when known), condition code (when known), description, quantity and photos are sent.",
              "The app never publishes. Nothing in this file is appended to your advert."]
    separator = "" if not private_notes or private_notes.endswith("\n\n") else "\n\n"
    write_text(path, private_notes + separator + "\n".join(lines) + "\n")


@dataclass(frozen=True)
class HandoffRow:
    """Local preparation only: never contains API responses or task information."""
    label: str
    value: str
    destination: str
    source: str


def labelled_values(content: str) -> dict[str, str]:
    """Read explicit labels, not numbers guessed from prose. Show duplicate conflicts."""
    values: dict[str, list[str]] = {}
    for line in content.splitlines():
        name, separator, value = line.partition(":")
        name = name.strip().strip("*- ").casefold()
        value = value.strip().lstrip("*").strip()
        if separator and value:
            entries = values.setdefault(name, [])
            if value not in entries:
                entries.append(value)
    return {key: entries[0] if len(entries) == 1 else "CONFLICT — " + " / ".join(entries)
            for key, entries in values.items()}


def handoff_rows(listing: Listing, notes: SellerNotes, research: str = "") -> list[HandoffRow]:
    """Explain every sent field and the private settings left for Seller Hub.

    Seller input takes precedence over research for manual guidance. listing.json
    alone determines the six uploaded fields; guidance can never silently change it.
    Legacy free-form notes remain visible in full in the preview.
    """
    seller, authored = labelled_values(notes.original), labelled_values(research)
    manual = "NOT SENT — complete in Seller Hub"
    sent = "WILL BE SENT — verify the actual draft"

    def guidance(label: str, *aliases: str, missing: str = "Not provided; review in Seller Hub.") -> HandoffRow:
        keys = [label.casefold(), *(alias.casefold() for alias in aliases)]
        for values, source in ((seller, "input.txt (seller)"), (authored, "output.txt (preparation guidance)")):
            found = list(dict.fromkeys(values[key] for key in keys if key in values))
            if found:
                value = found[0] if len(found) == 1 else "CONFLICT — " + " / ".join(found)
                return HandoffRow(label, value, manual, source)
        return HandoffRow(label, missing, manual, "Not supplied")

    rows = [
        HandoffRow("Title", listing.title, sent, "listing.json"),
        HandoffRow("Category ID", listing.category_id, sent, "listing.json"),
        HandoffRow("Asking price (GBP)", f"{listing.price_gbp:.2f}" if listing.price_gbp is not None
                   else "MISSING — no price will be sent.", sent if listing.price_gbp is not None else manual,
                   "listing.json → Start price (FixedPrice)"),
        HandoffRow("Condition ID", str(listing.condition_id) if listing.condition_id is not None
                   else "MISSING — choose the category's condition.", sent if listing.condition_id is not None else manual,
                   "listing.json"),
        HandoffRow("Quantity", str(listing.quantity), sent, "listing.json"),
        HandoffRow("Description", "Buyer-facing text in this preview/report; private notes are excluded.", sent, "listing.json"),
        HandoffRow("Photos", "The reviewed original photos, converted to JPEG copies.", sent, "Item folder"),
        guidance("Price guidance (GBP)", "Asking price (GBP)", "Suggested price (GBP)", "Price (GBP)",
                 missing="No separate guidance. The asking price above is the ONLY price the app sends."),
        guidance("Best Offer minimum (GBP)", "Minimum offer (GBP)", "Offers accepted above (GBP)"),
        guidance("Best Offer auto-accept (GBP)", "Auto-accept offer (GBP)", "Auto accept (GBP)"),
        guidance("Package dimensions (cm)", missing="MISSING — measure the PACKED parcel in cm."),
        guidance("Package weight (kg)", missing="MISSING — weigh the PACKED parcel in kg."),
        guidance("Postage service", "Delivery service", "Postage"),
        guidance("Postage charged to buyer (GBP)", "Postage price (GBP)", "Postage cost (GBP)"),
        guidance("Dispatch time"),
        guidance("Collection", "Local collection"),
        guidance("Item specifics"),
        HandoffRow("Location and account policies", "Review delivery, returns and payment policies.", manual, "Seller account"),
    ]
    return rows
