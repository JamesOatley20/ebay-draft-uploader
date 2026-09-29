# Storage boundary — app 3.0.2

## Retained preparation

Original photos, input.txt, listing.json, seller-authored/research portions of output.txt and batch.json remain local. The six listing fields and generic category/condition selections are unchanged. A version-3 batch manifest deliberately prevents the version-2 application from running against migrated work.

Generated persistent files are limited to local JPEG derivatives, preparation-only draft.csv (empty Item photo URL), preview.html, the LOCAL PREPARATION portion of output.txt, a constant run.lock, the fixed submission-guard.json and tool-path.txt. Migration can additionally recover only local listing/notes from a legacy snapshot. Migration markers contain fixed local text.

The guard is created and flushed BEFORE remote mutation. It has no account, time, task reference, result or response-derived branch. Every outcome leaves identical guard bytes. Only an explicit human review/release removes it. A lost guard, copied batch, renamed folder or disk failure can defeat local duplicate protection; it is not a server idempotency key.

## Session-only values

auth.Auth holds a manually supplied User token. There is no load/save/refresh credential flow. RuntimeItem holds task IDs, photo response records, status and messages. HTTPX headers, request/response bodies and cookies stay in its in-memory client. Result decompression uses BytesIO; no archive extraction occurs. The transmitted CSV is bytes, not a file handle or spooled temporary file.

Preparation completes before authentication. The network phase's only filesystem write is the fixed local guard; response data never reaches the local report/preview/CSV writers. The native Tk window displays session results without save/export, browser rendering or autosave. No raw API data goes to redirectable output. Unexpected thread and Tk callback exceptions do not print tracebacks. APIError stringification is static; details are for the in-memory window only.

The production HTTP client suppresses HTTPX/httpcore logging, disables environment proxies and redirects, verifies HTTPS certificates/hostnames, and constructs an SSLContext without consulting SSLKEYLOGFILE. The supplied launchers use Python -I -B. No token CLI argument, environment-file credential reader, telemetry, response-recording fixture, subprocess credential or app backup path exists.

Stopping does not retract a remote upload. A known task may be polled only while its process remains alive. After process loss, check Seller Hub Drafts/Reports. Never infer failure from an absent draft while processing may continue. No POST is automatically replayed after an uncertain result or 401.

## Migration scope and failure behaviour

migration.inspect_migration reads only explicitly selected batch roots and the named current-user eBayDrafts application-storage directory. It includes immediate item folders that are no longer in the batch selection, and recognised hashed item-storage directories. It does not recurse through arbitrary folders or backups. Existing path/link checks and resolved containment checks apply to writes/deletions.

The reviewed plan lists paths, never stored token/response values. It fingerprints inspected files and directory entries in memory to reject changed inputs. The CLI holds the same batch locks used by the old app; close older app instances before proceeding. Fixed migration markers block uploading after partial failure. Guards and recovered local preparation are written before legacy data is deleted. No rollback copies of prohibited data are made.

Cleanup includes sign-in.bin, state.json, result.bin, old upload CSVs, old previews, the recognised APP STATUS portion of output.txt and identifiable atomic-writer remnants. Authored content is preserved. Strong indicators of API/credential records outside an app-owned section are reported for manual review; this heuristic is not a classifier for every possible secret. Unrecognised storage, corrupt snapshots and ambiguous temporary files block automatic cleanup rather than being silently deleted.

An orphaned valid snapshot can yield recovered-listing.json and recovered-input.txt in its existing hashed directory. These contain only the original six-field listing and seller notes. Other legacy formats require targeted review; they are not guessed. Known external backups and independently maintained research corpora require their own review, without a whole-computer scan.

## Verification and limits

tests/run_tests.py exercises synthetic success, rejection, API errors, token refusal, uncertain writes, cancellation, malformed results, migration and six force-termination stages. Write instrumentation checks that only the fixed guard is written during authenticated work; generated-file scans check synthetic runtime canaries, including their UTF-16 representation. Migration tests check preservation, interrupted cleanup, changed files, scope and link refusal. Tests never call live eBay or record real responses.

This is an application-persistence guarantee, not forensic zeroisation of Python memory, Windows page/hibernation files, OS crash dumps, third-party clipboard/browser history or external backups. Deleting a historical file does not prove irreversible physical erasure. No system-wide setting or unrelated storage is modified.

## Exemption interpretation

The official account-deletion guide concerns user-data deletion and offers an opt-out for non-persisting applications. Its wording is broad and is not an explicit approval of this design. Explain that the app retains seller-supplied preparation and generic category/condition selections while discarding account/API runtime data; complete historical cleanup before making that representation.

Public listing research in the separate ChatGPT preparation workflow is not fetched by this app. Its existing research/pricing instructions are preserved. Public availability does not automatically establish licensing permission or remove privacy obligations for identifiable seller records; any such issue requires its own provenance review rather than deletion of ordinary listing fields.

Official references: [deletion/exemption](https://developer.ebay.com/develop/guides/sell/marketplace-user-account-deletion), [listing metadata](https://developer.ebay.com/develop/guides/sell/listing-metadata-guide), [category-tree reuse](https://developer.ebay.com/api-docs/buy/buy-categories.html), [API licence](https://developer.ebay.com/join/api-license-agreement), [OAuth](https://developer.ebay.com/develop/guides/sell/authorization), [Python TLS key logging](https://docs.python.org/3/library/ssl.html). Reviewed 28 September 2026.
