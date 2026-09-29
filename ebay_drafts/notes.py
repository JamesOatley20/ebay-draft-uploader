"""Read the seller's notes and keep private information out of the advert."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path
import re

from .files import read_text, write_text
from .listing import Listing

DEFAULT_CONDITION = "Used, in good condition and fully working."
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
        return cls.parse(read_text(folder / "input.txt", 32_000))

    @classmethod
    def parse(cls, original: str) -> "SellerNotes":
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
        return cls(original, values.get("condition") or DEFAULT_CONDITION, dimensions, weight, missing)


def update_preparation(folder: Path, messages: list[str],
                  listing: Listing | None = None, notes: SellerNotes | None = None) -> None:
    """Called only before authentication, with local preparation information."""
    path = folder / "output.txt"
    existing = read_text(path, 256_000) if path.exists() else ""
    private_notes = authored_prefix(existing.encode("utf-8")).decode("utf-8")
    lines = [PREPARATION_MARKER, "Local preparation only. This file does not record upload outcomes.", *messages]
    if listing:
        lines += ["", f"Title: {listing.title}", f"Category ID: {listing.category_id}"]
        if listing.price_gbp is None:
            lines.append("Price: MISSING. Set your asking price in Seller Hub before publishing.")
        else:
            price = listing.price_gbp
            minimum = (price * Decimal("0.8")).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
            accept = (price * Decimal("0.9")).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
            lines += [f"Asking price: GBP {price:.2f}",
                      f"Optional Best Offer suggestions: minimum GBP {minimum:.2f}; auto-accept GBP {accept:.2f}.",
                      "These offer settings have NOT been applied to eBay."]
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
