# eBay Drafts

Turn a folder of item photos into **reviewable eBay UK drafts**. ChatGPT prepares the wording; this Windows app uploads the photos and supported draft fields. It never publishes a listing.

**Windows · eBay UK · GBP · app 3.0.2**

Version 3 keeps eBay authentication and upload data **only in the current process**. You enter an OAuth User token each run. Upload results appear in a native session window and are not saved. Closing or crashing loses task references; an upload already sent to eBay may still finish.

## Before upgrading from version 2

1. Close older copies of the app. Check unresolved uploads in **Seller Hub → Drafts / Reports** before cleaning up their local history.
2. Run **Setup.cmd**, then **Start.cmd → 2. Review migration of old data**. Select the original batch folder.
3. Review the exact paths. Type **MIGRATE** to clean those locations. If REVIEW entries appear, resolve them locally and run migration again.
4. Repeat for other known batches. Do not claim old data has been removed from locations you have not checked.

Migration deletes old sign-in credentials, task history, result files, upload CSVs containing eBay photo URLs, app-owned upload-status sections and recognised temporary remnants. It preserves original photos, seller notes, listing fields, research notes and the app's installation path. It does not make copies of the deleted data.

Items with old upload artifacts receive a **local guard**. This is a reminder to resolve the previous attempt before another upload, not a saved eBay task or outcome. If a state file holds the only surviving local listing/notes, migration recovers just those preparation fields. Orphaned snapshots are recovered as recovered-listing.json / recovered-input.txt within their existing item-storage directory.

Only the selected batch roots and the current user's %LOCALAPPDATA%\eBayDrafts storage are inspected. There is no whole-computer, backup, browser-profile or cloud scan. Unrecognised files and links block automatic cleanup. Other backups are not certified clean. Ordinary deletion is not a forensic secure-erasure guarantee.

**Do not run an old app against migrated work.** Migration changes batch.json to version 3 so the version-2 app rejects it. The six listing fields are unchanged.

## One-time setup

Extract the app into a permanent folder you own, outside Program Files and outside your photo batches. Install Python 3.11 or newer for Windows, including its launcher, then double-click **Setup.cmd**.

Setup installs requirements.txt and registers the app location. It does not connect to eBay. This is a personal API tool, not an eBay-approved consumer service; production uploads require your own developer access and seller authorisation.

If you move or rename the app folder, close the app, remove only its `.venv` directory, and run **Setup.cmd** from the new location. Python virtual environments contain absolute paths and need recreating after a move ([Python documentation](https://docs.python.org/3/library/venv.html#how-venvs-work)). Setup also updates `%LOCALAPPDATA%\eBayDrafts\tool-path.txt`, which existing batch launchers use to find the app. Keep your batch folders and their local guards in place. Source files and launchers do not need machine-specific path edits.

| File or folder | What it is for |
|---|---|
| Start.cmd | Open a batch, review migration, or release a local guard. |
| Setup.cmd | Install dependencies and register this installation. |
| Open-eBay-Drafts.cmd | The batch's launcher, supplied in the ChatGPT overlay. |
| batch.json | Selects the ready and skipped item folders; version 3. |
| listing.json | The item's six prepared listing fields. |
| input.txt | Your condition, factual notes and packed parcel measurements. |
| output.txt | Local preparation and research notes; no upload outcomes. |
| .ebay-drafts/ | Local previews, JPEG derivatives, preparation CSVs and local submission guards. |

## Prepare your items

Make one folder per item, with **1–12 original photographs** and an input.txt file. Use this format:

~~~text
Condition:
Details:
Package dimensions (cm):
Package weight (kg):
~~~

Dimensions are the packed parcel's length × width × height in centimetres; weight is packed kilograms. Blank condition means used, in good condition and fully working unless notes or visible evidence contradict that declaration. This does not imply testing, battery health or a guarantee.

Create a ChatGPT project with the three guides in chatgpt/ and the supplied PROJECT-INSTRUCTIONS.txt. ZIP the item folders with their photos and input.txt. Exclude credentials, old uploads, .ebay-drafts and application files.

ChatGPT returns an overlay with the launcher, batch.json, READ-ME.txt and prepared item files. Preserve copies of your original photos and local preparation before overwriting them, but do not create new backups of old API/runtime artifacts. Migrate existing batches first.

Extract the overlay **into the original batch folder**, beside the original item folders:

~~~text
My eBay items/
    Open-eBay-Drafts.cmd
    batch.json
    Camera/
        input.txt
        photo.jpg
        listing.json
        output.txt
~~~

Keep the original item-folder and photo names. Skipped folders are excluded by batch.json even if they contain old listing files.

## Create drafts during one run

1. Double-click the batch's **Open-eBay-Drafts.cmd**, or choose a batch through Start.cmd.
2. Review the local preview and output.txt. Resolve preparation problems.
3. Type **DRAFT** to start. Enter a Production OAuth User token in the masked window.
4. Keep the session window open while eBay processes the upload. Read the results there.
5. Review the actual drafts in Seller Hub, finish remaining settings, then publish yourself if appropriate.

Start with one item. An accepted feed row is not proof that every setting is complete or that a listing has been published.

A **Stop this session** button stops further local work after the current request returns or times out. It does not cancel a task on eBay. If the window closes or the process crashes, check Seller Hub before another attempt. There is no cross-run task recovery.

The session stops its queue on the first rejected row, authentication failure, an uncertain outcome, or an unreadable result. Later items are not attempted. A rejection can indicate a shared upload problem, so resolve the cause before starting another run. An uncertain upload acknowledgement can still be checked using the task held in that same live process; it is never automatically resent.

Offline preparation checks validate the local fields and file structure; they do not prove eBay will create a draft. The current [official Feed quick reference](https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-quick-reference.html) lists `FX_LISTING` for creating drafts, and the app follows that route with schema `1.0` and CSV action `Draft`. An accepted task or uploaded file is not a successful draft: its row-level result must also succeed. If eBay cannot recognise the Draft task action, stop and resolve the feed integration with eBay Developer Support before retrying. Do not change the action to `Add`, which can publish a listing.

## Authenticate each run

Use your [eBay Developer Portal](https://developer.ebay.com/my/keys) Production keyset and its **User Tokens** controls to generate an **OAuth User access token** for the seller account. Request these scopes:

~~~text
https://api.ebay.com/oauth/api_scope
https://api.ebay.com/oauth/api_scope/sell.inventory
~~~

Use a User token, not an Application token or Auth'n'Auth token. The token is entered only in the app's masked prompt. Never put it in a command, environment file, listing file, ChatGPT conversation or ZIP.

The app does not save a token, refresh token, password, App ID or Cert ID. It does not run an OAuth callback or deletion server. Every new process requires token entry; normally generate a fresh token before a batch. Tokens typically last around two hours. If authentication expires or is refused, the queue stops; review Seller Hub before starting again.

Your eBay browser session and any clipboard/history tools are separate from the app. The app neither manages nor cleans them. Close token pages and handle your clipboard appropriately; do not save a token in a text file for this workflow.

## Local guards and another attempt

Before any remote upload for an item, the app writes a fixed **local guard**. This records your local authorisation of an attempt. It contains no eBay task ID, account, response, timestamp or outcome, and is identical after acceptance, rejection, cancellation or a crash.

A guarded item is never automatically resubmitted. To attempt it again:

1. Resolve the previous attempt in Seller Hub Drafts and Reports. An absent draft alone is insufficient while an upload may still be processing. Leave the guard in place and contact eBay support if uncertain.
2. Choose **Start.cmd → 3. Release an item after checking Seller Hub**.
3. Select the batch and exact item folder. Type **RELEASE** after completing that review.
4. Start a fresh review/upload session.

Changing listing.json does not update a draft already on eBay and does not clear a guard. Do not rename/move an item to bypass the guard. This is conservative duplicate protection, not an exactly-once delivery guarantee.

## What is uploaded and what stays local

The app sends photos and these six fields:

- title
- category_id
- price_gbp
- condition_id
- description
- quantity

The format is fixed-price Draft; price maps to Start price. Unknown price or an unverified condition code may be null. Title, verified category and finished description are required.

The preview's heading is the actual listing title, with its character count against eBay's 80-character ceiling. The local folder appears separately and is not uploaded as the title. Shorter, clear titles and single-paragraph descriptions are preparation preferences; they do not change the six-field contract. Version 3.0.2 stops the queue after a rejected row and keeps batch version 3 and the same storage/authentication behaviour.

Complete item specifics, parcel/delivery details, dispatch time, location, policies and any Best Offer settings in Seller Hub. output.txt and seller notes are not appended to the advert. Locally calculated offer suggestions are only a checklist.

The disk draft.csv is a **preparation export without photo URLs**. It contains your selected listing fields and a local SKU. The actual CSV containing temporary eBay-hosted photo URLs is built in memory and sent directly; it is never saved.

## Troubleshooting and command-line options

| Situation | Action |
|---|---|
| Missing app or Python environment | Run Setup.cmd from the app installation. |
| Legacy or unrecognised storage detected | Use migration; inspect any REVIEW entries. No eBay call is made until resolved. |
| Item held by a local guard | Resolve its earlier attempt in Seller Hub, then explicitly release it. |
| Token expired/refused | The session stops. Obtain a new token for a new run after checking existing work. |
| Row rejected or Draft task action not recognised | The queue stops. Resolve the reported error before retrying. For a task-action error, ask eBay Developer Support to confirm the supported draft feed type for the marketplace. Keep the local guard until the prior attempt is resolved. |
| eBay still processing or the app closed/crashed | Check Seller Hub. Restarting cannot recover the lost task reference. |
| No recognised result or uncertain outcome | Check Seller Hub Reports/support. Do not automatically repeat the upload. |
| Photo or listing changed during review | Start preparation again; do not bypass an existing guard. |

From the app directory:

~~~bat
.venv\Scripts\python.exe -I -B run.py --batch "C:\My eBay items" --preview
.venv\Scripts\python.exe -I -B run.py --batch "C:\My eBay items" --migrate
.venv\Scripts\python.exe -I -B run.py --migrate
.venv\Scripts\python.exe -I -B run.py --migrate --batch "C:\Batch one" --migration-batch "C:\Batch two"
.venv\Scripts\python.exe -I -B run.py --batch "C:\My eBay items" --release "Camera"
~~~

--migrate without a batch checks only the current user's eBayDrafts app storage. Migration always displays its plan before asking for MIGRATE. An interrupted migration remains blocked and can be resumed.

Exit codes: 0 completed/cancelled before upload; 1 items need attention; 2 setup/preparation/migration error; 3 session stopped with unfinished/unattempted work; 130 console interruption. They do not replace inspection of Seller Hub.

Limits: 100 items per batch, 12 photos per item, 64 MiB and 80 megapixels per original, at least 500 pixels on the longest side. JPEG copies are capped at 4096 pixels and 12 MiB. JPG/JPEG, MPO, PNG, WEBP, HEIC and HEIF are supported; original photos remain unchanged.

## Data retention and the eBay exemption

Version 3 is designed to support an exemption based on not retaining eBay account/API data. It retains seller-supplied preparation content and generic category/condition selections, plus the purely local guard. Authentication, upload IDs, image URLs, API responses and outcomes stay in process memory.

Remove historical runtime data in known locations before representing this behaviour to eBay. Explain the retained listing fields accurately. eBay's broad exemption wording is not a specific approval of this app, and this README does not claim approval.

[Data-storage boundaries, migration and tests](docs/DATA-STORAGE.md) describe the implementation and its limits. System paging, crash dumps, externally managed backups and browser/clipboard history are outside the app's storage guarantee.

## Development checks

Run the synthetic suite without eBay access:

~~~bat
.venv\Scripts\python.exe -I -B tests\run_tests.py
~~~

Tests use fake account data and temporary test directories, including force-terminated Windows subprocesses. They do not create real eBay drafts. Seller Hub feed uploads do not have a Sandbox equivalent; any live check must be a deliberately selected Production Draft, never publication.

References: [account deletion/exemption](https://developer.ebay.com/develop/guides/sell/marketplace-user-account-deletion), [OAuth authorization](https://developer.ebay.com/develop/guides/sell/authorization), [Feed workflow](https://developer.ebay.com/api-docs/sell/static/feed/fx-feeds-overview.html), [draft fields](https://pages.ebay.com/sh/reports/help/create-listings-bulk/#creating-draft-listings), [listing metadata](https://developer.ebay.com/develop/guides/sell/listing-metadata-guide). Rechecked 28 September 2026.

Released under the MIT License. Not affiliated with or endorsed by eBay or OpenAI.
