# Verification — 3.0.3 overlay

Prepared against repository commit `8c5ead7924c7664c8644b34432bc3d4712dfb728`.

## Executed checks

The original runtime and test files were retrieved through the connected GitHub repository at the supplied commit. Reconstructed source/test files were checked against their Git blob hashes before editing. This was not a Windows checkout or a live seller session.

| Check | Result |
|---|---|
| Original baseline suite | 43 tests passed. |
| Original tests on patched code | All 43 retained and passing. |
| Expanded suite | **63 tests passed, zero failures/errors/skips.** |
| Tk window lifecycle | Real Tk under Xvfb: successful synthetic run, token cancellation, pending stop and unexpected worker error. |
| Force termination | Original six stages exercised: photo, task, upload, pending, result and completed. |
| Runtime persistence instrumentation | Network-phase writes remained fixed guard bytes; synthetic runtime canaries absent from generated files, including UTF-16 checks. |
| Request/queue checks | Documented createTask route, marketplace header, multipart name/filename; rejection halts later submissions; uncertain upload not reposted. |
| New local preparation checks | Missing/empty notes; absent-file addition; changed output; offer precedence/conflicts; asking-price authority; old notes visible and HTML escaped. |
| New investigation checks | BOM/CRLF/header pinned; synthetic metadata/optional-column comparison; wrong market, Add, populated data and result-report rejection; identity/feed/unknown-state refusal; selected-item and prior-work confirmations. |
| Static preview | Generated synthetic HTML rendered in Chromium; table/body fit a 1280-pixel viewport; no HTML execution from escaped private notes. This was not a Windows file-launch test. |
| Package | Explicit member allowlist, per-file SHA-256 manifest, ZIP CRC/member checks and a fresh overlay reconstruction test. |

Command executed **from the repository root** in this Linux environment:

```sh
DISPLAY=:99 python -I -B tests/run_tests.py
```

The final suite output was:

```text
Ran 63 tests
OK
```

Environment: CPython 3.13.5, HTTPX 0.28.1 and Pillow 12.3.0. No application dependencies were added. The host did not have pillow-heif, so HEIC/HEIF decoding was not tested; the unchanged Windows requirements.txt includes that dependency. Synthetic photos use JPEG.

## Checks NOT executed

The requested Windows command could not be executed on this Linux host:

```powershell
.\.venv\Scripts\python.exe -I -B tests\run_tests.py
```

Run it in the installed Windows checkout. Windows-specific file locking, launcher/registration behavior, the actual local virtual environment and that machine's browser policies need the local check. The Linux equivalent and native Tk tests are not a claim of Windows end-to-end verification.

No eBay authentication, API call, outstanding-task reconciliation, production retry or actual draft inspection was performed. No fresh UK Seller Hub template was obtained. Synthetic CSVs are explicitly not official templates. There is no verified FX_DRAFT recommendation for EBAY_GB and no claim that production BAF.Error.5 is fixed.

No remote commit was made. The overlay is intended for review, testing and commit in the user's local repository. No project file deletion is required; no cleanup script removes guards or user data.
