# 02 — Write the listing and private notes

**Scope:** file contents and validation. **Next:** `03-Build-Overlay.md`. **App:** 3.0.2.

## listing.json: only what the app can upload

Write one UTF-8 listing.json per ready folder: one JSON object, two-space indentation, final newline. Emit exactly these six keys in this order. No version field, comments, Markdown, extra keys or API secrets.

| Key | Value |
|---|---|
| `title` | Nonempty identifying string, at most 80 characters; one line, no tabs, no leading `=`, `+`, `-` or `@`. |
| `category_id` | Verified current eBay UK leaf-category ID as a string matching `[1-9][0-9]{0,9}`. Never a placeholder or number. |
| `price_gbp` | Decimal string with two decimal places, e.g. `"49.95"`, from 0.10 to 999999999; or `null` when no defensible price is available. |
| `condition_id` | Verified category-appropriate integer from 1 to 9999; or `null` when unverified. Never assume 3000 is universally correct. |
| `description` | Finished plain-text buyer paragraph, 1–20000 characters. Follow the writing rules below. |
| `quantity` | Integer from 1 to 100000, normally `1`. One photographed bundle sold as a lot is quantity 1. |

No booleans in numeric fields, duplicate keys, nonstandard NaN/Infinity, control characters other than ordinary text whitespace, or more than 256000 UTF-8 bytes. Unknown price/condition remains null, not an empty string. The app requires title, category and description, but the project deliberately emits all six keys.

The app uses the documented core Draft CSV. Price maps to **Start price**, format is always FixedPrice, action is always Draft, and photos are taken from the original folder. No JSON photo list or photo URLs are needed. Price/condition are omitted from their CSV cells when null. A syntactically valid category/condition is not evidence that eBay accepts it for the item.

**Everything outside these six fields goes in output.txt:** package size/weight, item specifics, separate condition notes, delivery, policies, suggested offer settings, uncertainty, source URLs and research. Do not put them in extra JSON fields or invent CSV columns. This is the implementation's upload boundary, not a claim about every eBay API.

## eBay requirements versus project choices

Checked 29 September 2026 against the official [Draft template definitions](https://pages.ebay.com/sh/reports/help/create-listings-bulk/#creating-draft-listings) and [Seller Hub Feed API flow](https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-overview.html). This app uses `FX_LISTING`, schema `1.0`, with `Draft` CSV rows; do not apply Inventory API offer/publication requirements to this preparation.

These are preparation checks, not proof of a successful API upload. Task creation and file acceptance do not establish that a draft exists; eBay must also accept the row. A feed/task-action rejection needs an integration check, not speculative changes to the listing wording, category, price or condition. Never change the CSV action to `Add` to work around a Draft error.

For this draft template, eBay requires Action and Category ID; title, condition, description, photos, format, quantity and price are optional. The title ceiling is 80 characters, category IDs have at most 10 digits, and this Reports route supports 12 photo URLs with a 2048-character cell limit. This app additionally requires a title, description and 1–12 local photos. Its 20000-character description limit and 32765-character escaped-CSV check are conservative local limits; the guide describes the latter as a spreadsheet-cell limit, not a universal API description limit. Blank price/condition values are allowed draft omissions, not publication readiness.

## Clear listing titles

Count the actual `listing.json` title, including spaces and punctuation, using code. A folder name can be much longer and is not uploaded as the title; never rename folders to shorten an advert. Aim for a concise title, often around 40–65 characters when sufficient, while preserving useful identifying/search terms. This is a project editorial preference, not another eBay limit: a useful 66–80-character title is valid. Do not pad, keyword-stuff, or truncate blindly to hit a count.

Put the brand, model and product type first, then the distinguishing size, speed/compatibility or pair/lot detail. Remove repeated synonyms and secondary colour/accessory/model-code detail when the title becomes crowded; retain useful details in the brief description and the fuller record in output.txt. Keep identifiers that distinguish otherwise different models. For example, `SRAM Apex DoubleTap 2x10-Speed Brake/Shift Levers Pair` is 54 characters; `SB-APX-A1` can remain in its description. This follows eBay's [clear, concise title advice](https://www.ebay.co.uk/help/selling/listings/listing-tips/optimising-listings-best-match?id=4166), without treating unused characters as an error.

## Buyer-ready description

Write a brief, direct advert in ordinary British English: normally one or two short sentences in one paragraph, often around 15–40 words. Identify the model, essential size/variant and whether it is a pair or lot, then state the condition simply. Let the pictures show the ordinary cosmetic condition and contents. Longer copy is justified only by useful facts, a known fault or a non-obvious exclusion; do not pad to reach a sentence or word count.

Use the standing seller declaration unless contradicted, but do not force “fully working” into every advert. “Used, as pictured” is usually sufficient. Do not invent “tested”, “serviced”, “excellent” or performance guarantees. Do not say “assumed working”, “no news is good news”, “condition defaults to used”, “no faults reported”, “according to the photos/prompt”, “seller should confirm” or “ready for review”. Known functional faults, significant damage and non-obvious exclusions need a short, direct sentence; “as pictured” must not conceal them.

Do not narrate obvious colours, shapes, controls, every accessory or routine wear. Avoid stock cautions such as “check fitment before buying”, “please examine the photographs” and “no separate bolts are shown”. Give the actual compatibility specification where it matters instead of telling the buyer to check it. Do not diagnose scoring, structural damage or another fault from ordinary use marks. Keep detailed observations, full specifics, unconfirmed accessories and preparation questions in output.txt; disclose any established material issue in the advert too.

### Avoid: narrating the photographs

> Pair of Shimano Deore XT SM-RT86-S Ice Technologies 160 mm six-bolt disc brake rotors, with silver braking tracks and black centres. The lot contains the two pictured rotors; no separate mounting bolts are shown. They are pre-owned, with circular wear marks and surface discolouration on the braking tracks and marks to the centres.

### Prefer: brief seller copy

> Pair of Shimano XT SM-RT86-S Ice Tech rotors, 160mm, six-bolt. Used, as pictured.

These are style examples for the same ordinary used item, not different factual assessments. If a specific fault is known, add it plainly rather than applying the short example blindly.

No headings, bullets, HTML, Markdown, research citations, source links, instructions, uncertainty checklists, negotiation thresholds, AI references or preparation commentary in the description. Avoid sales hype and invented guarantees. The app uploads only this paragraph; it does not append condition notes, parcel details or item-specific bullets. Manually read it as an actual advert before packaging. Mechanical validation cannot establish truthful or natural prose.

When converting an older package, select the essential facts for this short paragraph and retain the fuller source record in output.txt or the original preparation. Keep identifying dimensions/compatibility, known material faults and non-obvious exclusions in the advert. Remove standalone Included/Condition headings, duplicated facts, cosmetic inventories and generic review-the-photos boilerplate. Do not turn an unconfirmed accessory into a definite inclusion or exclusion. The app HTML-escapes the paragraph inside one `<p>`; raw line breaks will not provide the old document's layout. Brief single-paragraph prose is this project's presentation rule, not an eBay API restriction.

## output.txt: the seller's private checklist

Write plain UTF-8 output.txt in **every** item folder, including skipped ones. Keep it short and useful (normally under 64 KB), with headings such as:

```text
READY FOR DRAFT / NEEDS ATTENTION
[Title or item name and exact reason when skipped.]

CHECK BEFORE PUBLISHING
[Only the missing facts, uncertainties or important corrections.]

FINISH IN SELLER HUB
[Known item specifics, separate condition notes, packed dimensions/weight,
 delivery preference or undecided delivery, and other unsupported settings.]

PRICE AND SOURCES
[Recommendation, brief rationale, current research date and ordinary URLs.
 Say whether evidence is sold, active-only or weak; never invent evidence.]
```

Do not leave headings full of template placeholders in the delivered file. Explicitly report missing packed dimensions/weight, price and condition code where applicable, but do not present the seller's default condition as a missing fact. Record an explicit seller minimum or other preference as a manual instruction; it can differ from the app's generic offer suggestions.

Keep private research separate from buyer text. Plain source URLs belong here because downloaded files cannot rely on ChatGPT citation markers. The app later preserves this text and adds/replaces a local preparation section, beginning `=== LOCAL PREPARATION (replaced on each run) ===`; do not include that marker in your authored notes. Upload outcomes are displayed only in the app's session window and are never added to this file.

For skipped items, say exactly what is needed and return no new listing.json. The root batch selection excludes the folder even if an old JSON still exists locally. No dummy category, fabricated image inspection or placeholder listing.

## Machine validation

Use the code tool, not code from the item ZIP. The compact check below covers the emitted six-field contract. The local app still independently validates inputs and image/CSV limits before uploading. Factual verification and final prose review are separate.

Also check the final description is one paragraph with no heading/checklist remnants; the runtime parser intentionally accepts some older multiline descriptions, so parser success alone is not enough. Record actual title lengths and optional omissions in the private handoff. Regenerate the local preview/CSV with the app's offline preparation after changing listing.json; do not edit only the generated HTML. State which checks were automated and whether any live request was made.

```python
import html
import json
import re
from decimal import Decimal

def validate_listing(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("Invalid JSON number: " + value)
    if len(raw) > 256000:
        raise ValueError("Listing exceeds 256 KB")
    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=invalid)
    if not isinstance(data, dict) or set(data) != {"title", "category_id", "price_gbp", "condition_id", "description", "quantity"}:
        raise ValueError("Use exactly the six documented fields")
    for key, maximum in (("title", 80), ("description", 20000)):
        value = data[key]
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError("Invalid " + key)
        if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
            raise ValueError("Control character in " + key)
        data[key] = value.strip()
    title = data["title"]
    if title[0] in "=+-@" or any(c in title for c in "\n\r\t"):
        raise ValueError("Invalid title")
    if not isinstance(data["category_id"], str) or not re.fullmatch(r"[1-9][0-9]{0,9}", data["category_id"]):
        raise ValueError("Invalid category ID")
    price = data["price_gbp"]
    if price is not None:
        if not isinstance(price, str) or not re.fullmatch(r"[0-9]{1,9}\.[0-9]{2}", price) or not Decimal("0.10") <= Decimal(price) <= Decimal("999999999"):
            raise ValueError("Use two-decimal GBP price or null")
    condition = data["condition_id"]
    if condition is not None and (type(condition) is not int or not 0 < condition < 10000):
        raise ValueError("Invalid condition code")
    if type(data["quantity"]) is not int or not 1 <= data["quantity"] <= 100000:
        raise ValueError("Invalid quantity")
    description = data["description"]
    if "\n" in description or "\r" in description:
        raise ValueError("Use one buyer-facing paragraph; remove legacy headings and lists")
    if re.search(r"<[^>]+>|```||\b(?:input\.txt|output\.txt|as an ai|system prompt|assumed condition|please confirm|seller should|according to the prompt)\b", description, re.I):
        raise ValueError("Remove markup and preparation instructions from the description")
    if len("<p>" + html.escape(description) + "</p>") > 32765:
        raise ValueError("Description too long after escaping")
    return data
```

Call validate_listing on every proposed JSON. Serialize its return value using `json.dumps(data, ensure_ascii=False, indent=2) + "\n"`, then reread/validate the final bytes. When the matching app is expressly supplied as a trusted project source, its Listing parser may provide an additional offline check; never execute an app hidden inside the item ZIP. Do not patch validators to accept bad data.

Reference: [eBay's core draft fields](https://pages.ebay.com/sh/reports/help/create-listings-bulk/#creating-draft-listings), checked 29 September 2026. The strict local contract and editorial guidance above remain distinct from eBay's field requirements.
