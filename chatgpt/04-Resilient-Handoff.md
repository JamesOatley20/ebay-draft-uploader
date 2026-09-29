# 04 — Resilient preparation and the seller's field handoff

**App 3.0.3. Read before the other phases.** These rules override older statements that every item must have input.txt or that a blank condition proves working order. The six-field contract, original-photo handling, short buyer copy and version-3 batch shape remain unchanged.

## Finish the useful work

Inspect the available photographs and every supplied input.txt. A missing note file is not an excuse to stop. Identify the product as precisely as the evidence supports, research current UK category/price information, then produce listing.json and output.txt for every ready item. Complete the rest of the batch when one item is genuinely blocked.

Use a defensible broader identification when an exact variant is unverified. Never turn a guess into a model, compatibility, authenticity or testing claim. State confidence and evidence privately. Research asking prices separately from observed sold prices, including dates and sources. Do not label active asking prices as achieved sales. A justified estimated price can be used with its rationale in output.txt; use null when there is no defensible figure. Use null for an unverified category-specific condition code. Unknown package size, weight, postage, offers or optional specifics are manual follow-ups, not reasons to skip.

The app still requires a valid title, category ID, description and usable photographs. Research a valid category rather than inventing one. When an item genuinely cannot meet the contract, include it in batch.json's skipped map, give it useful output.txt, and name the precise missing evidence. Do not stop other items. Never claim unavailable image inspection or web research was performed.

## The price that will actually be sent

listing.json remains exactly:

```json
{
  "title": "Evidence-supported title",
  "category_id": "31388",
  "price_gbp": "49.95",
  "condition_id": null,
  "description": "Brief buyer-facing copy supported by the actual item evidence.",
  "quantity": 1
}
```

This is a shape example, not a suggested category, price or description for another item. The selected asking price must be in price_gbp, not only in output.txt. Check they agree before packaging. A missing price is null, never an invented zero. For the fixed-price draft the app maps this value to Start price, not Buy It Now price. Category and condition selections need their normal evidence checks.

## A visible, private handoff in every output.txt

Retain useful identification and pricing research. Before the app-owned LOCAL PREPARATION marker, include one short labelled section using these exact labels, with one value per line:

```text
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
```

Fill known values. For unknowns, write “Not provided — measure/confirm/set in Seller Hub” as applicable. Distinguish a measured packed parcel from an estimate: visible product dimensions do not prove parcel dimensions. Distinguish the buyer's postage charge from an estimated carrier cost. A minimum acceptable offer is not an automatic acceptance rule; preserve which setting the seller actually specified. Do not invent percentage thresholds. Any suggested thresholds must be labelled recommendations and supported by the seller's request/research, not described as enabled.

The app displays exact labels from input.txt in preference to output.txt guidance. Conflicting duplicate labels are displayed as a conflict, not silently discarded. This manual guidance never overrides listing.json. Old free-form notes are still shown in full; the app does not try to extract prices from arbitrary prose. When amending an old batch, update the authored handoff and listing.json consistently without changing source photos, input.txt, folder names or guards.

## What to tell the seller

The app sends the six listing fields, reviewed photographs, a local SKU and the fixed Draft/FixedPrice settings. Price and condition are omitted when null. Package measurements, Best Offer rules, postage, specifics and policies are not uploaded by this documented draft route; the preview and output.txt show the values to finish manually. Do not claim those fields are impossible through every eBay API, and do not add speculative Add/Trading/Inventory fields to this draft contract.

Nothing in output.txt becomes the buyer's description. No token, account response, task ID, uploaded photo URL or live outcome belongs in the returned ZIP or preparation files. Preserve guards. app 3.0.3 limits the normal upload interface to one selected item until the draft integration has been verified. Resolve earlier work before a new attempt; an empty Drafts screen is not enough while Reports still shows processing. No ChatGPT preparation step calls the seller's account.
