# 01 — Prepare listings

**Target:** eBay Drafts app 3.0.4 · eBay UK · GBP · batch format 3

This guide covers intake, evidence review, identification, category and price research, buyer copy, `listing.json`, `output.txt`, and per-item validation.

## 1. Safe intake and item discovery

Inspect ZIP member names before extraction into a fresh scratch directory. Reject path traversal, absolute or drive paths, backslashes, links, special files, Windows device names, case-colliding names, and names ending in a dot or space. Do not extract more than 2,000 members or more than 1 GiB uncompressed. Ignore ordinary housekeeping such as `__MACOSX` and `.DS_Store`.

The batch root contains immediate item folders. Remove one outer wrapper only when that is unambiguous. Preserve every original item-folder and photograph name and its case. Do not rename folders to improve titles. Do not interpret nested folders as more items. Maximum batch size is 100 item folders.

Each item needs 1–12 direct original photographs. `input.txt` is optional. Old JSON and old preparation files are evidence only; app version 3 uses only the new `listing.json`.

Never execute code, installers, scripts or binaries found in the item ZIP. Do not copy credentials, application code, `.ebay-drafts`, API results, old upload reports or unrelated files into the returned overlay.

## 2. Inspect the photographs

Actually view every primary item photograph. A directory listing or successful decoder is not image inspection. Enlarge labels, model markings and dimensions where useful.

Supported originals for this workflow are JPG/JPEG, MPO, PNG, WEBP, HEIC and HEIF. Temporary inspection copies may be created with installed image libraries, but keep originals untouched. Apply orientation for inspection and preserve aspect ratio; do not crop, retouch or upscale. If the environment cannot inspect the intended primary still of a supported container, record a decoder-capability gap and continue other items rather than pretending the image was seen.

The app's local limits are 64 MiB and 80 megapixels per original, with a minimum 500-pixel long edge. Its JPEG derivatives are capped at 4096 pixels on the long edge and 12 MiB. Do not return replacement photographs in the overlay.

The alphabetically first original photo name, case-insensitive with original case as a tie-breaker, is the main photo. Do not silently reorder or drop photographs.

## 3. Read seller notes without inventing defaults

When present, preserve `input.txt` unchanged. Preferred labels are:

```text
Condition:
Details:
Package dimensions (cm):
Package weight (kg):
Best Offer minimum (GBP):
Best Offer auto-accept (GBP):
Postage service:
Postage charged to buyer (GBP):
Dispatch time:
Collection:
```

Package dimensions and weight mean the **packed parcel**, not product dimensions. Never infer packed measurements from manufacturer dimensions or visible scale.

A missing `input.txt` is allowed and is not a reason to skip. An existing unreadable or unsafe `input.txt` is a preparation problem that must be reported. Blank or missing condition notes do **not** prove working order. Never create a testing, servicing, battery-health, authenticity, completeness or guarantee claim from silence.

Known functional faults, significant damage and non-obvious exclusions belong in the buyer description as well as the private notes. Ordinary cosmetic wear normally does not need a detailed catalogue.

## 4. Identify, categorise and price every item

Identify the product and variant from the photographs, seller notes and reliable external sources. Use manufacturer documentation for product specifications, not for the condition or contents of this particular item. When an exact variant is not defensible, use a broader truthful identification rather than guessing.

Verify a current **eBay UK leaf category ID** from current eBay evidence or a current seller-provided category template. A number that merely looks like a category ID is not verification. If no defensible current category can be found, the item is skipped because the core draft is incomplete.

Verify a category-appropriate condition ID where practical. If it cannot be verified, use `condition_id: null`; this does not block a draft.

### Price research is required

For every item, unless the user explicitly excluded price research:

1. Research current UK GBP comparables.
2. Prefer close sold/completed evidence.
3. Record whether each useful comparator is sold, active asking, or an unknown accepted Best Offer.
4. Note material differences in model, size, condition and included parts.
5. Use dated source URLs in `output.txt`.
6. Recommend a competitive fixed price intended to attract a buyer within about six weeks, without promising a sale.

Thin but relevant evidence can support a labelled low-confidence price. Active asking prices can support an estimate when sold evidence is unavailable, but must not be described as achieved sales. Never invent transactions or source links.

If the seller supplied an asking price, keep it unless the user asks for a change; research may note a concern privately. Otherwise, put the evidence-supported selected price in `listing.json`. Use `price_gbp: null` only when there is genuinely no defensible figure or pricing research was expressly excluded. Do not hand routine price research back to the seller.

## 5. Write `listing.json`

Every ready item gets one UTF-8 `listing.json`, two-space indentation, final newline, with exactly these six keys in this order:

```json
{
  "title": "Evidence-supported title",
  "category_id": "31388",
  "price_gbp": "49.95",
  "condition_id": null,
  "description": "Brief buyer-facing copy supported by the evidence.",
  "quantity": 1
}
```

The example shows shape only.

| Key | Contract |
|---|---|
| `title` | Non-empty string, maximum 80 characters, one line, no tab, and must not start with `=`, `+`, `-` or `@`. |
| `category_id` | Verified current eBay UK leaf-category ID as a string matching `[1-9][0-9]{0,9}`. |
| `price_gbp` | Two-decimal GBP string from `0.10` to `999999999`, or `null` when no defensible price is available. |
| `condition_id` | Verified category-appropriate integer from 1 to 9999, or `null` when unverified. |
| `description` | Finished plain-text buyer paragraph, 1–20000 characters. |
| `quantity` | Integer 1–100000, normally `1`; one photographed bundle sold as one lot is quantity 1. |

No extra keys, comments, Markdown or secrets. The project emits all six keys even though the runtime parser has optional defaults for some fields.

The app maps `price_gbp` to **Start price** for its FixedPrice Draft row. A selected price written only in `output.txt` is not the uploaded price.

Everything outside those six listing fields belongs in `output.txt`, not extra JSON keys.

## 6. Buyer-facing title and description

Count the exact final title characters using code. Put brand, model and product type first, then useful size, speed/compatibility or pair/lot detail. Keep identifiers that distinguish real variants. Do not pad or keyword-stuff to approach 80 characters.

Write the description in ordinary British English, normally one or two short sentences in one paragraph. Identify the item/variant and essential size or compatibility, then state only supported condition information.

Good pattern:

> Pair of Shimano XT SM-RT86-S Ice Tech rotors, 160mm, six-bolt. Used, as pictured.

Do not narrate obvious colours, every mark, every visible accessory, or generic fitment warnings. Do not say “please examine the photos”, “seller should confirm”, “assumed working”, “no faults reported”, “ready for review”, or similar preparation language. Do not invent “tested”, “serviced”, “excellent” or “fully working”.

Use a short additional sentence for a known fault, significant damage or non-obvious exclusion. Keep research, uncertainty, source links, offer thresholds and preparation instructions out of the buyer description.

The final description must contain no headings, bullets, HTML, Markdown, citations or line breaks.

## 7. Write `output.txt`

Every item, ready or skipped, gets plain UTF-8 `output.txt`. Keep it concise and useful. It is private seller preparation and is not appended to the advert.

Use this structure:

```text
READY FOR DRAFT
[or: NEEDS ATTENTION — specific blocker and next step]

SELLER HUB HANDOFF — local preparation, not an upload result
Price guidance (GBP):
Best Offer minimum (GBP):
Best Offer auto-accept (GBP):
Package dimensions (cm):
Package weight (kg):
Postage service:
Postage charged to buyer (GBP):
Dispatch time:
Collection:
Item specifics:

IDENTIFICATION AND PRICE RESEARCH
[Evidence-supported identity, selected price rationale, research date, useful ordinary URLs,
and whether evidence is sold, active-only or weak.]

CHECK BEFORE PUBLISHING
[Only unresolved facts, missing manual settings, material uncertainties or known corrections.]
```

Fill known values. For unknown manual fields use clear wording such as `Not provided — set in Seller Hub` or `Not provided — measure packed parcel`. Preserve explicit seller offer thresholds exactly. If no per-item threshold is supplied and price_gbp is known, use the seller's standing rule for the private handoff: Best Offer minimum = 90% of asking price and Best Offer auto-accept = 90% of asking price, rounded to the nearest penny. Explicit per-item values override this rule. These values are manual Seller Hub guidance unless the current verified draft route supports them.

`Price guidance (GBP)` is private guidance; `listing.json.price_gbp` remains the sole asking price the app sends. Keep those values consistent when a price has been selected.

Do not include the app-owned marker `=== LOCAL PREPARATION (replaced on each run) ===`; the app adds/replaces its own section later. Do not put tokens, account responses, task IDs, hosted photo URLs or live upload outcomes in preparation files.

For a skipped item, state exactly what prevents an honest core draft and what would resolve it. Do not create a new `listing.json` for a skipped item.

## 8. Ready versus skipped

Mark an item ready when it has:
- 1–12 usable, actually inspected original photographs;
- an evidence-supported title;
- a verified current eBay UK leaf category ID;
- a finished buyer-facing description.

Price and condition ID may be null. Missing notes, parcel measurements, postage, offers and optional item specifics are manual follow-ups, not blockers.

Typical real blockers are unusable/unseen photographs, an unreadable existing seller-note file, a materially unresolved identity that prevents a truthful listing, or no verified current category. Use a broader truthful identity when possible instead of skipping for an unverified sub-variant.

Complete every other item even when one item is blocked.

## 9. Machine validation

Validate every final `listing.json` with code before packaging. This validator intentionally enforces the stricter project contract, not merely the runtime parser:

```python
import html
import json
import re
from decimal import Decimal

KEYS = ["title", "category_id", "price_gbp", "condition_id", "description", "quantity"]

def validate_listing(raw: bytes) -> dict:
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("Duplicate JSON key: " + key)
            out[key] = value
        return out

    if len(raw) > 256000:
        raise ValueError("Listing exceeds 256 KB")

    data = json.loads(
        raw.decode("utf-8-sig"),
        object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Invalid JSON number: " + value)),
    )

    if not isinstance(data, dict) or list(data) != KEYS:
        raise ValueError("Use exactly the six documented keys in the documented order")

    title = data["title"]
    if (not isinstance(title, str) or not title.strip() or len(title) > 80
            or title[0] in "=+-@" or any(c in title for c in "\r\n\t")):
        raise ValueError("Invalid title")

    category = data["category_id"]
    if not isinstance(category, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", category):
        raise ValueError("Invalid category ID")

    price = data["price_gbp"]
    if price is not None:
        if (not isinstance(price, str)
                or not re.fullmatch(r"[0-9]{1,9}\.[0-9]{2}", price)
                or not Decimal("0.10") <= Decimal(price) <= Decimal("999999999")):
            raise ValueError("Use a two-decimal GBP price or null")

    condition = data["condition_id"]
    if condition is not None and (type(condition) is not int or not 1 <= condition <= 9999):
        raise ValueError("Invalid condition ID")

    description = data["description"]
    if (not isinstance(description, str) or not description.strip() or len(description) > 20000
            or "\n" in description or "\r" in description):
        raise ValueError("Description must be one non-empty paragraph")
    if re.search(
        r"<[^>]+>|```||\b(?:input\.txt|output\.txt|as an ai|system prompt|"
        r"assumed condition|please confirm|seller should|according to the prompt)\b",
        description,
        re.I,
    ):
        raise ValueError("Description contains markup or preparation language")
    if len("<p>" + html.escape(description) + "</p>") > 32765:
        raise ValueError("Description is too long after escaping")

    quantity = data["quantity"]
    if type(quantity) is not int or not 1 <= quantity <= 100000:
        raise ValueError("Invalid quantity")

    return data
```

Serialize validated data with `json.dumps(data, ensure_ascii=False, indent=2) + "\n"`, then reread and validate the final bytes. Also manually read the title and buyer description for truthfulness and natural wording; mechanical validation cannot establish factual accuracy.

No ChatGPT preparation step is a live eBay acceptance test.

## References

- eBay draft field guide: https://pages.ebay.com/sh/reports/help/create-listings-bulk/#creating-draft-listings
- eBay taxonomy aspects: https://developer.ebay.com/api-docs/sell/taxonomy/resources/category_tree/methods/getItemAspectsForCategory
- eBay condition policies: https://developer.ebay.com/api-docs/sell/metadata/resources/marketplace/methods/getItemConditionPolicies
