# Faction-owned speech, local test implementation

The first launcher preview incorrectly grouped speech by race. This implementation
uses Royalist, Council, Nationalist, Ceyah and Fallen ownership, plus a common
campaign/neutral language. The race-based preview is superseded; its output files
are retained only as historical artifacts.

## Native boundary

Kohan II 1.3.72 only. The supported stock executable SHA-256 is
`1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45`.
The verified runtime image has base 0x460000, while the saved Ghidra export has
base 0x400000; all patch offsets below are RVAs.

- FXCCreateSFX execution at RVA `0x2c602e` resolves its event owner handle from
  context +0x0c, its source/target actors at +0x10/+0x20, and dispatches audio via
  the call at RVA `0x2c61d9` to RVA `0x1e96a`.
- Eight stack arguments are preserved. Argument 1 is the audio definition;
  argument 5 is the already resolved owner kingdom. The actor fallback is argument
  3. The native audio manager uses actor virtual +0x108 to obtain a kingdom when
  the explicit owner is absent. The router follows this same boundary.
- Do not reinterpret actor +0x78 as a kingdom. The original group +0x108 getter
  at RVA `0x22f1f7` reads +0xe8; the virtual getter handles actor subclasses.
- A live kingdom's faction instance is +0x23c; instance +4 is its definition,
  and definition +8 is UTF-16 IDS. This also matches the existing read-only
  activity reader. Nation/race at kingdom +0x240 is not read by the router.
- Audio DataCollection is database +0x584. Its native IDS dictionary is +0x30
  (buckets/count at +0x30/+0x34). The router uses the original case-insensitive
  multiply-by-33 IDS hash and bounded collision traversal. Missing variants retain
  the original definition.

The import-free x86 payload only changes the first audio argument. It preserves
the original manager, source/target, position, context, callee stack cleanup,
return value, registers, flags and FP/SSE state. It writes only its own diagnostic
counters; it does not write actors, factions, game RNG, orders or network state.

The launcher verifies the stock EXE, exact new-process path/start time, native
call bytes and four registered generated cues before installation. It allocates
the payload separately, suspends the new game's threads for the five-byte call
replacement, checks instruction pointers, verifies writes and restores protections.
Failure restores the original call before resuming threads. No existing match is
selected for attachment. The process-local patch disappears when the game exits.

## Resources and preferences

All non-English voice packages are selected for custom speech. Source packages
remain verified and complete. Generated managed resources retain parallel
`data/Audio/PawVoices/{en,ru,de,fr}/...` recordings. English comes from the game's
original Data.rwd. Generated audio definitions preserve the original cue settings
and reference language-specific files, falling back to English for unavailable
translated recordings. The common language also supplies the original paths for
campaign/neutral playback and non-routed audio.

The generated module is versioned from original archive, verified package and
effective audio-table hashes. Changing faction preferences reuses these recordings.
The installer records their hashes and removes/restores them transactionally.
Switching to normal speech removes the generated definitions and restores the
ordinary package selection. Cached source/generation files remain reusable.

`FactionVoiceLanguages` is separate from the obsolete race-preview map. A new
local `-VF` configuration suffix preserves the six faction/common choices.
These personal choices are excluded from social gameplay configuration exchange.
They survive normal speech selections and launcher restarts.

## Rebuilding and evidence

```
python game/faction-voices/build.py --legacy <verified-legacy-analysis> --out <owned-native-output>
python game/faction-voices/test_native.py --legacy <verified-legacy-analysis> --native <owned-native-output>
```

Copy the resulting FactionVoices.bin/json into launcher Assets after checking the
manifest hash. `build.py` requires the existing verified runtime, TinyCC and local
Keystone/Capstone/pefile dependencies. It does not modify an installed game.

Native emulator checks: **1,864**, two relocated images, all five factions and
four languages, different source/target ownership, absent-owner virtual fallback,
same human cue changing Royalist/Council owners, missing cue fallback and ABI.
A separate owned 32-bit Windows fixture validates native cue-readiness inspection,
thread suspension/context, guarded installation and continued real x86 dispatch.

Full launcher suite: **39,089**. Actual published voice-resource integration:
**5,620** checks. WPF preference fixture: **14** in each of six languages; public
copy fixture: **38** in RU and EN. Evidence is under top-level outputs with the
`faction-voices-` prefix.

Live audio, a real match, multiplayer interoperability and replay compatibility
have not been accepted in this turn. Native fixtures and installed-file hashes
are not evidence of audible playback or network compatibility. No release, feed,
server or normal game installation was changed by this development.
