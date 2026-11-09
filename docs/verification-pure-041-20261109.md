# Pure 0.4.1 — Vanilla / Immortals

The accepted 0.4.1-beta.12 compiler inputs and public package hashes were frozen
before rebuilding. Four helpers use the lobby-only native module and omit
PAW_PURE_RECOVERY. Multiplayer saves and client copies retain their original
native resource. Other feature values match beta.12 exactly, excluding the
stable version/channel and removed recovery metadata. No city automation,
foundation distribution, extra slots or fractional kingdom points are included.

Offline validation: 1008 guarded native composition installs at three image
bases, 477 random-map transaction cases, 24 valid/invalid lobby configurations,
and preservation of the 80-byte native save-copy Block path in 12 compositions.
The standalone lobby codec/ABI checks also passed. Three package manifests and
static payload parity were checked against the downloaded beta.12 archives.

Live acceptance uses the exact packaged helpers through the existing private
reflection startup harness: Vanilla and Immortals each reached the menu,
created a new LAN-hosted match, advanced simulation, wrote a native save and
exited normally. Both reported the multiplayer-saves module ready. No assertion
or desync was detected. Only one native peer was active in accepted runs.
The source fixtures retain old launch-menu metadata; runtime/lobby identity is
0.4.1, while a production launcher apply writes current menu metadata.

Earlier pair and single-peer attempts were stopped by the runner's commit
reserve guard, and are retained. They are not game-crash evidence or current
two-peer acceptance. The accepted Immortals rerun used reduced private graphics
cache/shadow settings; gameplay files and the shipped helper were unchanged.
No network client-copy/disconnection scenario completed in this update's live
runs. Historical beta.12 coverage does not replace that limitation.

Evidence: outputs/pure-041-050-20261109/stable-helpers-r2/,
stable-stage/, stable-publication/, G:/PawPure041QA-20261109/vanilla-single-r1/
and G:/PawPure041QA-20261109/immortals-trace-r1/.
The published source-input archive contains frozen compiler inputs and no key.
Installed player files, saves, system settings and unrelated processes were
not changed. Catalog promotion preserves Arcane and launcher payloads and
leaves both legacy catalog envelopes byte-identical.
