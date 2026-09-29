# 03 — Package the overlay and hand it over

**Scope:** final ZIP and Windows launcher. **App:** 3.0.3. Requires the prepared outputs from phases 01 and 02, with any omitted review disclosed.

## Exact overlay contents

Include only these entries, directly at the ZIP root without an extra enclosing folder:

```text
Open-eBay-Drafts.cmd
batch.json
READ-ME.txt
<original ready folder>/listing.json
<original ready folder>/output.txt
<original skipped folder>/output.txt
```

There is exactly one listing.json for each ready item, and no new listing.json for a skipped item. Every item gets output.txt. Do not include photographs, input.txt, old JSON copies, settings, credentials, code from the item ZIP, the app, a virtual environment or .ebay-drafts. Do not delete/rename source files. Preserve original item-folder names and case.

This overlay replaces matching listing.json/output.txt, batch.json and the launcher. Tell the user to preserve original photos and local preparation before extraction; a launcher cannot recover overwritten files. Migrate existing batches through app 3 first, and do not create new backup copies of old credentials or API/runtime artifacts. Existing differently named JSON files are left untouched and ignored by app version 3.

## batch.json

One UTF-8 object with exactly these three keys:

```json
{
  "version": 3,
  "items": ["Exact ready folder name"],
  "skipped": {"Exact skipped folder name": "Specific reason and next step."}
}
```

The names above are placeholders illustrating the shape, not delivered entries. Use only actual immediate item-folder names; no paths. A name occurs exactly once across items/skipped. Maximum 100 folders total, 256000 UTF-8 bytes, 2000 characters per skip reason. Both collections may be empty only when the archive genuinely contains no items, with an explanation. Every discovered item folder must be accounted for. A fully skipped batch has an empty items list and still gets its reports.

This small selection file prevents an old listing in a skipped/unreviewed folder from being uploaded. It is not a signature or a photo-fingerprint manifest. The app validates current files, takes upload copies, and detects changes during local review. Keep original photos/input unchanged between ChatGPT preparation and local review; changes to item facts should be reviewed and prepared again.

## Windows launcher

Copy the fixed template below verbatim. It requires no user-supplied Windows paths: Setup.cmd registers the installed app in the current user's local application data. The launcher runs only that app and uses its own folder as the batch root. Do not substitute a sandbox path or add installers, network calls, dynamic evaluation, credential collection, administrator elevation or execution-policy changes.

Write the .cmd with CRLF line endings and UTF-8 for double-click use. The app owns the local preview, one exact item selection, RESOLVED and DRAFT confirmations, token entry for this process and a native session-results window. It does not save authentication, task IDs or upload results. A fixed local guard requires explicit review before another attempt.

### Open-eBay-Drafts.cmd

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

## Check the actual returned archive

Build a fresh ZIP from an explicit output allowlist, never by recursively zipping the scratch workspace. Reopen it, run its CRC check, inspect the complete member list and reread every archived JSON through the phase-02 validator. Confirm batch names match the actual source folders, ready/skip sets are disjoint, and each required output exists exactly once. Reject path traversal, duplicate/case-colliding archive members and unexpected files. Verify the launcher matches the template and encoding requirements. Original photos and input.txt must not have changed.

Put a short READ-ME.txt in the ZIP: actual ready/skipped counts, which named files are replaced, and the same beginner steps used below. Identify app 3.0.3 and say that version-2 app executables must not be used with these batches. Existing version-2 batches require migration; the version-3 manifest and six listing fields are unchanged. Do not add another batch review document duplicating every output.txt. Validation is file/contract validation, not a live eBay listing test.

For an authorised in-place conversion/amendment, update listing.json and the authored output.txt consistently, then regenerate the current app preview/CSV offline when the installed app is available. Preserve originals, input.txt, folder names, guards and any original manual package kept as source evidence. Identify which files are current: old dashboards do not automatically follow edits. The current preview uses the actual upload title as its heading, shows its character count and labels the local folder separately. A longer local folder label is not a title-limit failure.

Check the buyer copy against phase 02's brief seller-copy example before handing it over. Do not expand it back into a cosmetic inventory or add fitment/review cautions while packaging. Keep full specifics and review notes private, with known faults and non-obvious exclusions also stated briefly in the advert.

Before packaging, apply 04-Resilient-Handoff.md: missing optional notes must not stop useful preparation, selected prices belong in listing.json, and every output.txt must expose the remaining manual settings. Do not claim the BAF.Error.5 integration problem is fixed by this overlay preparation.

## Final handoff

Provide the real downloadable ZIP after verifying it exists. Keep the final message brief, usually under 120 words, with the actual ready/skipped counts and any important question grouped once. Give this process in plain English:

Preserve original photos and local preparation; migrate existing batches before extracting a new overlay. Extract the ZIP **into that original folder**, not a new overlay subfolder. Double-click Open-eBay-Drafts.cmd. Read the field handoff in the preview and each output.txt. Select one exact ready item. Resolve prior remote uploads in Seller Hub Drafts and Reports before confirming RESOLVED and DRAFT; then enter a Production OAuth User token for this run. Keep the session window open for results. Finish remaining fields in Seller Hub and review before publishing. Run Setup.cmd from the app once if it is not installed yet.

Do not make the user copy shell commands or provide path variables during ordinary use. If their organisation blocks a script, use its approved process rather than circumventing policy. If eBay is still processing, keep the current session open or check Seller Hub after closing. Restarting cannot recover a task. Do not tell users to erase a guard or submit a second copy: resolve the outcome in Seller Hub before using the app's explicit release action.

If inspection, research or machine validation was unavailable, state exactly which check was not done. Deliver useful notes but never claim unseen photos were inspected or an unverified executable overlay was fully validated. There are no account calls in this ChatGPT workflow and no permission to publish.

Reference: [eBay draft-feed workflow](https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-overview.html).
