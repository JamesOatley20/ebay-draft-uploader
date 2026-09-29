# 02 — Build the overlay and hand it over

**Target:** eBay Drafts app 3.0.3 · batch format 3

This guide starts only after every discovered item has been classified ready or skipped and every proposed `listing.json` has passed the validator in `01-PREPARE-LISTINGS.md`.

## 1. Exact overlay contents

Build a fresh ZIP from an explicit allowlist. The ZIP root contains only:

```text
Open-eBay-Drafts.cmd
batch.json
READ-ME.txt
<original ready folder>/listing.json
<original ready folder>/output.txt
<original skipped folder>/output.txt
```

There is exactly one `listing.json` for each ready item and no new `listing.json` for a skipped item. Every item gets `output.txt`.

Do **not** include photographs, `input.txt`, old JSON files, credentials, settings, application code, a virtual environment, `.ebay-drafts`, account data, API responses, upload reports, or temporary inspection files. Do not delete or rename source files. Preserve original item-folder names and case exactly.

The overlay replaces matching `listing.json`, `output.txt`, root `batch.json` and `Open-eBay-Drafts.cmd` when extracted into the original batch. Existing differently named old JSON files are left untouched and ignored by app version 3.

## 2. `batch.json`

Write one UTF-8 object with exactly these keys:

```json
{
  "version": 3,
  "items": ["Exact ready folder name"],
  "skipped": {
    "Exact skipped folder name": "Specific reason and next step."
  }
}
```

Use actual immediate item-folder names only, never paths. Every discovered item folder must occur exactly once across `items` and `skipped`. Names are case-sensitive source names, and the combined set must have no case-insensitive duplicates.

Maximum 100 folders total, 256000 UTF-8 bytes, and 2000 characters per skip reason. A fully skipped batch has an empty `items` list and still gets all reports. Do not leave a skipped or unreviewed folder out of the manifest merely because an old listing file exists there.

## 3. Fixed Windows launcher

Write `Open-eBay-Drafts.cmd` exactly as below, with CRLF line endings and UTF-8. Do not substitute sandbox or user-specific paths, add installers, make network calls, collect credentials, request elevation or change execution policy.

```bat
@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
if not exist "%LOCALAPPDATA%\eBayDrafts\tool-path.txt" goto missing_app
set "Tool="
set /p "Tool="<"%LOCALAPPDATA%\eBayDrafts\tool-path.txt"
if not defined Tool goto missing_app
if not exist "%Tool%" goto missing_app
for %%I in ("%Tool%") do set "Python=%%~dpI.venv\Scripts\python.exe"
if not exist "%Python%" goto missing_app
"%Python%" -I -B "%Tool%" --batch "%~dp0."
set "Result=%ERRORLEVEL%"
pause
exit /b %Result%
:missing_app
echo Double-click Setup.cmd in the eBay app folder first, then open this file again.
pause
exit /b 2
```

The installed app owns local image conversion, preview generation, preparation CSV creation, selected-item review, `RESOLVED` and `DRAFT` confirmations, masked token entry, session results and local submission guards.

## 4. `READ-ME.txt`

Keep `READ-ME.txt` short. It must contain:
- actual ready and skipped counts;
- a warning that extracting the overlay replaces matching `listing.json`, `output.txt`, `batch.json` and the launcher;
- app target 3.0.3 / batch version 3;
- the beginner next steps from section 6 below;
- a reminder that preparation/validation is not proof of a live eBay draft.

Do not duplicate every item's research into another batch-level report.

## 5. Validate the actual returned ZIP

Before delivery:

1. Build the ZIP from an explicit allowlist, not by recursively zipping the scratch workspace.
2. Reopen the ZIP and run its CRC check.
3. Inspect the complete member list.
4. Reject traversal, absolute paths, duplicate members, case-colliding members and unexpected files.
5. Confirm every discovered source item is represented exactly once in `batch.json`.
6. Confirm every ready item has one `listing.json` and one `output.txt`.
7. Confirm every skipped item has one `output.txt` and no new `listing.json`.
8. Reread every archived `listing.json` and run the strict validator from guide 01 again.
9. Confirm every selected `price_gbp` agrees with the authored price guidance/research; do not leave a chosen price only in `output.txt`.
10. Confirm every buyer description is one concise paragraph and contains any known material fault or non-obvious exclusion.
11. Verify the launcher matches the fixed template exactly.
12. Confirm original photographs and `input.txt` files were not modified.

State honestly if image inspection, web research, category verification or machine validation was unavailable. Never claim an unperformed check.

## 6. Current app handoff

The ChatGPT workflow performs no seller-account calls and never publishes.

The app uses the documented `FX_LISTING` / schema `1.0` route with CSV action `Draft` and format `FixedPrice`. At this repository state, live Production draft creation is **not verified**. Offline preparation, a successful local validator, task creation or file acceptance does not prove that eBay created a usable draft. Do not change the action to `Add`, and do not switch to an unverified `FX_DRAFT` route based on speculation.

The app sends the six listing fields, reviewed JPEG derivatives, a local SKU and its fixed Draft/FixedPrice settings. Price maps to **Start price**. Price and condition are omitted when null.

Package measurements, Best Offer settings, postage, item specifics, dispatch time, collection, location and account policies are not sent by this documented route. The preview and `output.txt` show them for manual completion. Do not claim those fields are impossible through every eBay API.

### What the seller does next

Tell the seller, in plain English:

1. Preserve the original photographs and ordinary local preparation. If an old version-2 batch still exists, migrate it through app 3 before extracting a new overlay.
2. Extract the overlay ZIP **into the original photo-batch folder**, not into a new overlay subfolder.
3. Double-click `Open-eBay-Drafts.cmd`. If the app has never been installed, run `Setup.cmd` once from the app folder first.
4. Read the preview and each item's private handoff.
5. Select **one exact ready item**.
6. Resolve all previous remote work for that item in Seller Hub **Drafts and Reports** before continuing. An empty Drafts page alone is not enough while Reports may still be processing.
7. Only after that review, confirm `RESOLVED`, then `DRAFT`.
8. Enter a Production OAuth **User** token in the app's masked prompt for that session. Never send the token to ChatGPT or place it in files.
9. Keep the session window open for results.
10. Review the actual Seller Hub draft, complete the remaining manual fields and policies, and publish only when satisfied.

A local guard is conservative duplicate protection. Do not tell the seller to delete, bypass, rename around or otherwise evade it. If a prior remote outcome is unresolved, do not recommend another upload. After the remote outcome is genuinely resolved, the app's explicit release action may be used as designed.

Closing or restarting the app cannot recover a discarded remote task reference and does not undo work already sent to eBay.

## 7. Final ChatGPT reply

Deliver the real downloadable ZIP and keep the user-facing message concise. Include:
- ready/skipped counts;
- the ZIP link;
- any important unresolved question grouped once;
- the extraction location and first launcher step;
- the one-item / prior-remote-work / `RESOLVED` / `DRAFT` / session-only User-token sequence;
- a reminder to finish manual fields in Seller Hub and review before publishing.

Do not ask for Windows paths. Do not claim a successful upload, a fresh official-template comparison or live API acceptance unless that event was actually observed in the authorised environment.

## References

- eBay Feed quick reference: https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-quick-reference.html
- eBay Feed workflow: https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-overview.html
