# eBay Drafts

Turn item-photo folders into reviewable eBay UK drafts. ChatGPT prepares the wording and pricing; this Windows app uploads photographs and supported draft fields. It never publishes a listing.

**Windows · eBay UK · GBP · app 3.0.3 · batch format 3**

**Production draft creation is still unverified.** Two reported attempts failed with `BAF.Error.5` and a third was stopped with its remote outcome unknown. This release repairs the local field handoff and adds safer investigation controls; it does not claim that eBay's draft-routing failure has been fixed. Read [the investigation and next-test gates](docs/DRAFT-FEED-INVESTIGATION.md) before any new upload.

## What changed in 3.0.3

The preview now shows a field-by-field handoff, including asking price, offer thresholds, packed dimensions/weight and postage. Each row identifies its source and whether it will be sent or must be entered in Seller Hub. Full private research and seller notes are visible in the preview, not hidden behind a file link. Selected manual values also appear in the native session window.

Missing input.txt no longer blocks an otherwise prepared item. Unknown condition or measurements are not invented. The app no longer manufactures 80%/90% offer thresholds. Seller-labelled input takes precedence over research guidance, while listing.json remains the sole authority for uploaded fields. Changes to output.txt or the addition of previously absent input.txt invalidate the review.

The normal upload interface now requires **one deliberately selected item**, confirmation that previous remote work is resolved, and the existing DRAFT confirmation. It does not silently submit the whole batch. The lower-level queue still stops after the first rejection or uncertain result; its existing tests remain. The draft route and transmitted CSV are deliberately unchanged pending authoritative evidence.

## One-time setup

Install Python 3.11 or newer for Windows, including its launcher. Keep the app in a permanent folder you own, outside Program Files and outside photo batches. Double-click **Setup.cmd** to install requirements.txt and register the app location. Setup does not connect to eBay. This is a personal developer tool, not an eBay-approved consumer service.

After moving the app, close it, remove only its `.venv` folder and rerun Setup.cmd in the new location. Virtual environments contain installation-specific paths. Do not move or rename item folders or remove guards to make another upload possible.

Start.cmd opens the app menu. Open-eBay-Drafts.cmd is the launcher placed beside a photo batch by ChatGPT. Both use the installed app; item ZIPs must not contain executable application code.

## Prepare a photo batch

Use one immediate folder per item with 1–12 original photographs. Add input.txt when possible:

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

Measure the **packed parcel**, not just the product. Missing measurements stay unknown. Blank condition is not evidence of working order. A missing note file is allowed, but an existing unreadable file needs correction rather than silently being ignored.

Create a ChatGPT project using PROJECT-INSTRUCTIONS.txt and **all four guides** in chatgpt/. Read 04-Resilient-Handoff.md before the other phases; it supersedes older mandatory-input/default-condition wording. For an existing ChatGPT project, replace its copied project instructions and add the new fourth guide; installing the code overlay does not update that project automatically. Upload a ZIP of item folders and photographs. Exclude credentials, application code, `.ebay-drafts`, old upload reports and account data.

ChatGPT should inspect available evidence, research identity/category/pricing, write brief buyer copy, and complete every defensible item. It must not halt the whole overlay for optional missing information, invent an exact variant or claim unperformed research/testing. Each ready item gets listing.json; every item gets private output.txt. A blocked item is named explicitly in batch.json's skipped map.

The returned item overlay contains the launcher, batch.json, READ-ME.txt and prepared item files, but not replacement photographs or input.txt. Preserve original photographs and ordinary preparation before overwriting matching files. Do not make new backup copies of historical API/runtime data. Extract the overlay **into the original batch folder**, not into an extra overlay subfolder. Keep names and case unchanged.

## Review and upload

Double-click Open-eBay-Drafts.cmd or choose a batch through Start.cmd. Review the preview, particularly the **What the app sends / what you must finish** table. The preview is preparation, not a record of successful uploads.

Select one exact ready item folder. First resolve all earlier work in Seller Hub Drafts and Reports. Only then confirm **RESOLVED**, confirm **DRAFT**, and enter a Production OAuth User token in the masked native prompt. An empty Drafts page alone is not evidence that an upload failed while remote processing might continue. Do not proceed with a test merely because this release passes offline checks.

Keep the session window open for results. A successful feed row still needs review in the actual Seller Hub draft, including photographs, price and incomplete settings. The app never publishes. Closing, stopping or crashing does not undo remote work; stopping cannot cancel a task on eBay. The token and task references are not recovered in a new process.

## Which values are sent?

listing.json accepts only **title, category_id, price_gbp, condition_id, description, quantity**. Title, category and buyer description are required by this app. Price and an unverified category-specific condition code may be null. Unknown quantity defaults to one only when that matches the item/lot being offered.

The app also sends the reviewed JPEG copies, a local SKU and the fixed Draft/FixedPrice settings. `price_gbp` maps to **Start price**, not Buy It Now price. This distinction matters for fixed-price listings. A price mentioned only in output.txt does not change the serialized price: amend listing.json before review, or set it manually on eBay.

Parcel measurements, Best Offer rules, postage, item specifics, dispatch time, collection, location and account policies are **not sent by this documented draft route**. This is not a claim that every eBay API lacks those features. Their supplied values are displayed for manual completion. output.txt and input.txt are never appended to the buyer description. No arbitrary prose is interpreted as an executable offer rule.

Explicit input.txt labels take precedence over equivalent output.txt guidance. Duplicate conflicting labels are marked as conflicts. Old free-form research remains visible in full. No percentage-based offer settings are calculated or enabled automatically.

## Authentication and storage

Generate a **Production OAuth User access token** for your seller account through the eBay Developer Portal's User Tokens controls, with these scopes:

```text
https://api.ebay.com/oauth/api_scope
https://api.ebay.com/oauth/api_scope/sell.inventory
```

Do not use an Application token or Auth'n'Auth token. Never put a token in commands, environment files, ChatGPT, listing files or ZIPs. Authentication is entered only in the masked window. The app does not save or refresh credentials, run an OAuth callback, or replay a write after authentication failure.

Authentication, task IDs, hosted photo URLs, API responses and results remain in memory. Native session results are not saved or rendered into browser files. The disk draft.csv has blank photo URLs; its transmitted counterpart is built only in memory. HTTP logging, environment proxies, redirects and TLS key logging are disabled by the existing network layer.

Persistent files are limited to seller preparation, JPEG derivatives, preview.html, preparation-only draft.csv/output.txt sections, a fixed run lock, a fixed submission guard and the installed tool path. [DATA-STORAGE.md](docs/DATA-STORAGE.md) describes the unchanged storage boundary and legacy cleanup; [the 3.0.3 investigation](docs/DRAFT-FEED-INVESTIGATION.md) records the additional local-only displays. Browser/clipboard history, paging, crash dumps and external backups are not controlled or forensically erased by this app. No eBay exemption approval is claimed.

## Guards and migration

A fixed local guard is written and flushed **before any remote mutation** for an item. It contains no task, account, timestamp or outcome. All outcomes leave the same bytes. A guarded item is never automatically resubmitted. Neither editing a listing nor installing this overlay clears it.

Resolve the prior task/draft first. Then use **Start.cmd → 3. Release an item after checking Seller Hub**, select the original batch and exact folder, and confirm RELEASE. Do not delete guards, rename items, copy batches to evade them, or release a guard because a draft is temporarily absent. The guard is conservative duplicate protection, not a server idempotency key.

Before upgrading version-2 batches, close old app instances, resolve unresolved uploads, then choose **Start.cmd → 2. Review migration of old data**. Review the listed paths and confirm MIGRATE. Unrecognised files, ambiguous content and links stop automatic cleanup. Repeat for other known batches; there is no whole-computer scan.

Migration removes recognised old credentials, task history, responses, uploaded-photo CSVs and app-owned status sections without copying them into backups. It preserves photographs, local listing/notes/research and installation paths, and can recover local fields from legacy snapshots. Fixed migration markers keep interrupted cleanup blocked until reviewed and resumed. Do not run old executables against migrated batches.

## Offline checks and selected-item command

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -I -B tests\run_tests.py
.\.venv\Scripts\python.exe -I -B run.py --batch "C:\My eBay items" --preview
.\.venv\Scripts\python.exe -I -B run.py --compare-template "C:\Downloads\fresh-UK-draft-template.csv"
```

The comparison command is offline and accepts a blank UK CSV only. It compares columns, Action parameters, metadata positions/fingerprints, BOM and line endings. It does not authenticate, adopt the template, change the serializer or prove the file came from eBay. Exit 1 means differences to review; exit 2 means the file could not safely be compared. Get the actual file from the UK seller account's **Seller Hub → Reports → Upload → Get template → Listings → Create new drafts → CSV**.

Only after the investigation's prerequisites have been completed:

```powershell
.\.venv\Scripts\python.exe -I -B run.py --batch "C:\My eBay items" --item "Camera"
```

This command still requires RESOLVED and DRAFT, a session-only token, clean storage and an unguarded reviewed item. It cannot clear a guard. The UI limits this release to one selected item while live compatibility remains unverified.

Existing migration/release commands remain available:

```powershell
.\.venv\Scripts\python.exe -I -B run.py --batch "C:\My eBay items" --migrate
.\.venv\Scripts\python.exe -I -B run.py --migrate
.\.venv\Scripts\python.exe -I -B run.py --migrate --batch "C:\Batch one" --migration-batch "C:\Batch two"
.\.venv\Scripts\python.exe -I -B run.py --batch "C:\My eBay items" --release "Camera"
```

Without --batch, --migrate inspects only the current user's eBayDrafts app storage. Normal exit codes remain 0 for completion/cancellation before upload, 1 for items needing attention, 2 for setup/preparation errors, 3 for unfinished session work, and 130 for console interruption. Codes are not proof of a Seller Hub draft.

The original 43 tests plus new regressions use synthetic data only. See [verification results](docs/VERIFICATION-3.0.3.md). They cannot prove live Feed compatibility. Seller Hub feed uploads have no Sandbox equivalent; never test with Add.

Limits remain 100 batch items, 12 photos per item, 64 MiB/80 megapixels per original and a 500-pixel minimum long edge. JPEG copies are capped at 4096 pixels and 12 MiB. JPG/JPEG, MPO, PNG, WEBP, HEIC and HEIF are supported. Original photographs remain unchanged.

## Official references

[eBay Feed quick reference](https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-quick-reference.html) · [Feed workflow](https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-overview.html) · [Draft-field guide](https://pages.ebay.com/sh/reports/help/create-listings-bulk/#creating-draft-listings) · [OAuth](https://developer.ebay.com/develop/guides/sell/authorization) · [Python environments](https://docs.python.org/3/library/venv.html#how-venvs-work).

Draft-feed references reviewed 29 September 2026. MIT License. Not affiliated with or endorsed by eBay or OpenAI.
