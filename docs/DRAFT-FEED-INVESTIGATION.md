# Draft feed investigation — 3.0.3

Base: `8c5ead7924c7664c8644b34432bc3d4712dfb728` (3.0.2). Review date: 29 September 2026.

## Outcome and limits

**The local preparation/handoff defects are repaired. The production BAF.Error.5 failure is NOT verified resolved.** No production request, task recovery, guard release or draft creation was performed while preparing this overlay. The third reported upload remains an unknown remote outcome. No fresh authenticated UK draft-template bytes were available for an actual comparison. This repository must not imply otherwise.

There is a distinction between the **officially documented route** and a route proven to work for this seller's current UK account. The former is FX_LISTING / schema 1.0 / Draft; the latter remains unestablished. The public sources reviewed do not establish FX_DRAFT as the supported UK replacement. Do not replace uncertainty with an undocumented default or a claim of a live fix.

## Evidence

| Question | Finding | Evidence / limit |
|---|---|---|
| Which feed is publicly documented for drafts? | FX_LISTING; schema 1.0. | Official quick reference [1]; workflow [2]. |
| Which unpublished action? | Draft, not Add. | Official draft guide [3]; workflow [2]. |
| Is the current multipart shape documented? | `file`, filename with extension, form-data. | Official workflow [2]; synthetic request regression checks the actual adapter. |
| Is FX_DRAFT an official UK requirement? | Not established. | The linked community thread contains second-hand support advice; it is not official documentation or proof for EBAY_GB [4]. |
| Must description/price be rewritten for BAF.Error.5? | The error alone does not establish that. | It reports task-action routing; changing product facts is not an evidence-based remedy. The exact server cause still needs confirmation. |
| Can Sandbox verify this? | No equivalent Seller Hub feed upload support is documented. | Official workflow [2]. Production Draft-only testing requires prior-work reconciliation. |
| Is there a verified successful draft? | No. | User's report; no live seller session was available in this investigation. |

The route is now defined once in feed.py and imported by create_task and poll_task. It is not configurable to Add or an unverified fallback. BAF.Error.5 produces specific in-memory guidance and cannot be counted as success even when accompanied by an inconsistent success label. Missing/wrong task identity or feed type, unknown states and partially processed states stop the queue for review. Only the documented pending states CREATED, QUEUED and IN_PROCESS continue polling [5].

## Serializer comparison actually completed

The following checks are against the **published field guide**, not a downloaded UK template:

| Aspect | App 3.0.2 and 3.0.3 transmission | Published-guide comparison |
|---|---|---|
| Action header | `Action(SiteID=UK|Country=GB|Currency=GBP|CC=UTF-8)` | Locale/currency declaration retained. Exact fresh UK header, optional markers and Version metadata remain unverified. |
| Headers after Action | Custom label (SKU), Category ID, Title, Condition ID, Item photo URL, Description, Format, Quantity, Start price | All are documented draft fields [3]. |
| Additional optional draft columns | UPC and Buy It Now price are not emitted | The six-field contract supplies no UPC. Buy It Now price is for an auction with that option, not FixedPrice [3]. |
| Data | Exactly one Draft row; FixedPrice format | Consistent with published draft action/format [3]. |
| Price | price_gbp → Start price, two decimals; empty when null | Correct documented fixed-price field [3]. Moving it to Buy It Now price would be wrong. |
| Description | HTML-escaped buyer text inside a simple paragraph | Simple HTML is documented; private preparation remains excluded [3]. |
| Metadata | No #INFO or other metadata records | No fresh UK template was obtained; necessity and exact values are not established. |
| Encoding | UTF-8 BOM, CRLF, final CRLF | Existing serializer retained. The public guide does not establish the exact fresh UK BOM requirement. |
| Upload | In-memory bytes, multipart file/draft.csv | File field/extension shape matches [2]. |

Changing BOM, adding guessed #INFO rows or switching feedType solely because a different marketplace's community report mentioned them would not establish compatibility. This overlay **does not claim a completed fresh-template comparison or bundle a supposed official UK fixture**. Test templates are explicitly synthetic.

The offline `--compare-template` command accepts the seller's blank UK CSV and reports exact header order and Action parameters, missing/additional documented columns, metadata record positions and cell counts/fingerprints, BOM and line endings. Metadata text itself is not echoed. It rejects populated item rows, Add actions, result reports, foreign marketplaces and unknown columns. It never sends or adopts the file. Structural equality is not proof of authenticity, API routing or draft creation.

## Local handoff changes

The original price mapping was already correct. Its availability in a generated CSV did not prove it had reached a rejected draft. Parcel measurements and offer guidance were local, but the preview only linked to output.txt, and app-generated 80%/90% offer suggestions could compete with supplied values.

The preview now displays all sent fields and remaining manual settings with their source. The native session shows the selected item's local handoff too. Seller-labelled input overrides preparation guidance, never listing.json. Duplicate labels are shown as conflicts; older free-form notes remain visible in full. Price guidance is explicitly separate from the asking price serialized from listing.json. Default offer percentages are removed. Missing input.txt is allowed; missing notes or blank condition do not imply fully working order or parcel measurements. Source files are not fabricated.

The source-review fingerprint now includes output.txt and records absent input.txt, so changing manual advice or adding notes after review prevents submission. The listing JSON still permits exactly the original six fields. The app does not inject shipping/offer/Trading fields into an unverified draft template.

## Storage and safety

The original DATA-STORAGE.md boundary remains in force. New handoff rows and preview content derive only from local seller preparation before authentication. No runtime result enters output.txt, HTML or draft.csv. The template comparison is an unauthenticated local-file check, not an API diagnostic export. It creates no file.

Tokens, task IDs, uploaded photo URLs, HTTP/result data and runtime status remain memory-only. The only network-phase disk write remains the same fixed guard, written before remote mutation and unchanged across outcomes. Guard/migration implementations, no-replay rules, TLS settings and six-field validation are preserved. No task IDs, diagnostic responses or credentials are bundled as fixtures. Synthetic test results are not production diagnostic responses.

The normal UI/CLI requires one exact ready item and RESOLVED followed by DRAFT. RESOLVED is a **human attestation**, not an automated account audit, and does not release a guard. No automatic multi-item production path is exposed while compatibility is unverified. The lower-level queue and its stop-after-first-rejection contract are retained and tested.

## Gates before the next live attempt

1. **Resolve earlier remote work first.** Keep guards. Inspect the original seller account's Drafts and Reports for both rejections and the stopped processing attempt. An absent draft does not prove failure. When Reports cannot establish the outcome, have eBay Support resolve it. Do not rename/copy an item or clear guards as a workaround. This overlay cannot recover task IDs discarded with a previous process.
2. **Obtain the actual UK template.** In the same seller's UK Seller Hub: Reports → Upload → Get template → Listings → Create new drafts → CSV. Keep it blank and inspect it offline. Run `--compare-template` and review any differences; do not automatically change or upload the template. Do not substitute the US community example. Request official confirmation of marketplace/feedType/schema and any required metadata/encoding if the published route still fails.
3. **Make an evidence-backed correction, not a blind retry.** A successful template comparison alone is insufficient while the routing failure remains unexplained. Incorporate only a supported correction after reviewing its effect on the final Draft-only validation, getTask feed check and preparation-only CSV classification. Never switch to Add or publish-then-end. Do not run a new test only because the version changed.
4. **Select one reviewed, unguarded item.** After the old outcome is resolved, use the existing explicit release action only where appropriate, then select exactly one item. Do not upload the same item both manually and through the API without reconciling the first attempt. Do not persist task identifiers or downloaded diagnostic responses to conduct this investigation.
5. **Verify the actual Seller Hub draft.** Keep the live session open through processing. Check row-level acceptance and inspect the draft's title, description, quantity, price, condition and photographs. Confirm that no active listing was created. Complete manual settings separately. A 2xx create/upload response, COMPLETED task alone or passing synthetic test is not the acceptance criterion.

## Question for eBay Developer Support

For Production EBAY_GB, what feedType and schemaVersion are officially supported for a Create new drafts CSV with Action=Draft? The public quick reference currently names FX_LISTING/1.0, while this seller received BAF.Error.5, “Unable to find Task Action Id for task Draft”. Please resolve the outstanding processing attempt before a retest and confirm whether the UK route requires a change, and the exact official UK template header/metadata/encoding. A community claim of FX_DRAFT is unverified. The application must remain unpublished/draft-only and cannot retain tokens, task IDs or diagnostic responses.

This is a question prepared for the seller, not a support ticket sent during this work.

## Sources

[1] [Official quick reference](https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-quick-reference.html).

[2] [Official Seller Hub feed flow](https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-overview.html).

[3] [Official creating-draft-listings field guide](https://pages.ebay.com/sh/reports/help/create-listings-bulk/#creating-draft-listings).

[4] [User-supplied community thread](https://community.ebay.com/forum/ebay-developers-program-57950/topic/fx_listing-api-fails-with-baferror5-unable-to-find-task-action-id-for-task-draft-473250/). The FX_DRAFT advice is second-hand, not authoritative support for a UK route change.

[5] [Official FeedStatusEnum](https://developer.ebay.com/api-docs/sell/feed/types/api:FeedStatusEnum).
