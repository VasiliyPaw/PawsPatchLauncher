# Finalizing launcher 0.7.8 and its independent patch releases

`tools/FinalizePatchChannels078.py` stages four signed production feeds. It does not build software, execute the launcher or game, retrieve credentials, create releases or tags, upload, commit, or push. The default invocation leaves canonical files unchanged.

Inputs are a completed candidate directory, the full source commit, and the downloaded CI distribution's `launcher-artifact.json` and final `PawsPatchLauncher.exe`. The artifact must identify that commit and version 0.7.8. The executable's hash, size, product/version metadata and Authenticode state must match the CI manifest. An unsigned CI release is accepted only when the manifest explicitly records unsigned mode, as in `CompleteLauncherArtifact.ps1`.

The source commit must exist locally. Its launcher project must declare 0.7.8, and its `docs/release-0.7.8.md` must match the working copy after Git line-ending normalization. RU/EN launcher news and the new launcher history entry come from that committed document. Existing patch histories, package identities, compatibility metadata and per-mod guides remain exactly as in the candidate.

For example, fill the source commit and local CI paths before running:

```powershell
python tools/FinalizePatchChannels078.py `
  --candidate '..\patch-channels-078\candidate-final-r14-guide' `
  --source-commit '<full verified source commit>' `
  --launcher-artifact '<downloaded CI distribution>\launcher-artifact.json' `
  --launcher-exe '<downloaded CI distribution>\PawsPatchLauncher.exe' `
  --dotnet 'G:\CodexData\projects\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe' `
  --signing-dir '<existing signing directory>' `
  --out '..\patch-channels-078\finalized-078-review'
```

Every run requires a new output directory. `--published-at YYYY-MM-DDTHH:MM:SSZ` fixes the finalization date for reproducibility; otherwise the current UTC time is used. ECDSA envelope signatures can differ between runs even when their payload bytes match.

The output includes:

- `feeds/legacy/` and `feeds/v2/`: four final production payloads and verified signatures.
- `canonical/feed/`: the V2 combined changelog history and shared patch-guide files intended for the root authoring paths.
- `rollback/feed/`: exact copies of all seven current canonical files.
- `release-notes.md` and `finalization.json`: committed notes, input identities, preservation checks and the proposed target changes.

Add `--verify-public` for read-only verification that all four release tags point to the supplied commit, the seven patch ZIPs and three launcher release assets have the expected downloaded bytes, and the public canonical feeds still match the candidate's source generation. This uses public HTTP GET requests only. The three launcher release assets are the EXE, distribution ZIP and `launcher-artifact.json`.

Only an explicit `--promote` changes local canonical files. It always requires the public checks, repeats public-feed and local-input checks immediately before replacement, and creates an exclusive `feed/history/before-launcher-0.7.8-<commit-prefix>/` rollback directory. Existing rollback history is never overwritten. It updates the four legacy/V2 feeds, the root V2 changelog history and both shared patch-guide files. The embedded `Assets/mod-guides.json` remains unchanged.

Promotion replaces individual files atomically. If a later replacement or signature check fails, files already replaced by this invocation are restored when their bytes still belong to this invocation; another writer's intervening changes are never overwritten. The rollback directory is retained even after failure, so an interrupted generation requires review before another promotion attempt. A successful local promotion still does not publish or push anything.
