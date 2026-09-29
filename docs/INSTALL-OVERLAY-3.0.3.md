# Install and commit the 3.0.3 source overlay

This ZIP is for the **application checkout**, not a photo batch. It replaces the listed application/project-guide files and adds investigation/tests/docs. It does not contain item listings, photographs, credentials, task IDs, API responses or a virtual environment. It deletes nothing; no self-deleting removal script is needed.

**This is not a verified production draft-upload fix.** Read DRAFT-FEED-INVESTIGATION.md before any live attempt. Installing or testing this overlay never resolves the stopped remote task or releases a guard.

## Install

Close older app instances. In PowerShell, from the local application checkout, verify the base commit and clean worktree **before extraction**:

```powershell
Set-Location 'C:\code\repos\ebay-draft-uploader'
if ((git rev-parse HEAD).Trim() -ne '8c5ead7924c7664c8644b34432bc3d4712dfb728') {
    throw 'Wrong base commit. Review the patch against your branch before installing.'
}
if (git status --porcelain) {
    throw 'Working tree is not clean. Review existing changes before overwriting files.'
}
```

Extract `ebay-draft-uploader-3.0.3-overlay.zip` directly into this checkout and allow the listed source files to be replaced. ZIP entries start with README.md, run.py, ebay_drafts/, chatgpt/, docs/ and tests/; there is no enclosing app folder. Do not extract into an item batch. No Setup rerun is needed solely for this patch because requirements are unchanged; use Setup.cmd when the environment is missing.

Verify the extracted files and run the user's Windows offline command:

```powershell
$manifestPath = 'docs/OVERLAY-3.0.3.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
foreach ($file in $manifest.files) {
    $actual = (Get-FileHash -LiteralPath $file.path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $file.sha256) { throw "Overlay hash mismatch: $($file.path)" }
}
.\.venv\Scripts\python.exe -I -B tests\run_tests.py
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed. Do not upload or commit a passing-test claim.' }
git diff --check
if ($LASTEXITCODE -ne 0) { throw 'Review whitespace errors before committing.' }
git diff --stat
git diff
```

Read new files too: ordinary git diff does not include untracked files. `git status --short` identifies them. OVERLAY-3.0.3.json lists all source/doc payload files and their checksums; the manifest itself is the sole checksum-list exception to avoid a self-referential hash.

## Commit only this overlay

After reviewing the changes and passing the local suite:

```powershell
$paths = @($manifest.files | ForEach-Object { $_.path }) + @($manifestPath)
git add -- $paths
if ($LASTEXITCODE -ne 0) { throw 'Staging failed.' }
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Review staged changes before committing.' }
git diff --cached --stat
git commit -m 'Improve draft handoff and guard unresolved feed investigation'
```

These commands create a local commit; use the repository's normal review/push process afterward. No remote commit or push was performed during preparation of this overlay. Do not stage seller batches, API data or unrelated files.

## Update the ChatGPT preparation project

Replace the project's copied PROJECT-INSTRUCTIONS.txt content, update 03-Build-Overlay.md and add 04-Resilient-Handoff.md. Keep phase 01 and 02; the new project rules explicitly override their older mandatory-input/default-condition wording. Installing this repository overlay alone does not update an existing ChatGPT project.

## Before any new production test

Resolve the old remote work in the original Seller Hub account. Obtain the fresh blank UK draft template and run the offline comparison. Secure an evidence-backed answer to the routing problem rather than retesting merely because the version changed. Only then use the documented single-item flow, with existing guards and RESOLVED/DRAFT confirmations intact. Never use Add, persist diagnostic responses or rename/copy items to bypass a hold.
