# Paw's Patch 0.4.0-beta.5 verification

Source: `83580491ab99f108c5d2e0a455fb76840cd13c16`.
Release: `patch-0.4.0-beta.5` (Arcane Wars beta only).

- Canonical build produced all eight helpers with the existing native regression
  suites, plus 21,312 sync-wrapper checks at three ASLR bases.
- The separate real x86 probe passed first/repeated calls and the complete
  512-byte floating-point state comparison. Native file IO was stubbed in both
  probes; this is not a reproduced multiplayer desync.
- Launcher Release suite: 27,485 checks passed.
- Diagnostic archive fixture: 321 checks passed, including byte-for-byte inclusion
  of the fresh native synclog among older replay logs.
- Installation matrix: 73,728 selections, 15,024 unique plans, 69 verified
  archives, eight helpers, 30 preflights and 45 successful transitions. Tests ran
  in an isolated fixture, preserving its save sentinel and original game EXE.
- Real local startup: installed the four signed candidate packages through
  `ModuleInstaller.ReconcileAsync`, preserving applied settings. The main menu
  displayed Arcane Wars 0.82.1.8 and Paw's Patch 0.4.0-beta.5. Read-only memory
  verification confirmed all three diagnostics hook sites and the native writer
  trampoline. The game then exited normally through its menu.
- No multiplayer match was started and no desync was induced in the live game.
  Startup validation does not establish that the underlying divergence is fixed.

Tested helper SHA-256:
`4CB93F91BE5857056CE4C7568F7FA349F1C8D5F19D592396725FB1A5FF09A009`.

The initial manual two-file startup attempt was correctly rejected by installed
version validation before the game started. The successful test used the complete
signed packages and normal transactional installation; no compatibility guard
was bypassed or weakened.

Only four Arcane Wars beta packages change: `pawpatch-core`, `player-colors`,
`desync-continue`, and `common-ui`. Their changed payload files are the runtime
helpers and patch version metadata. Gameplay data and the AI native payload are
unchanged from beta.4. Stable, other mods, and launcher 0.8.9 stay unchanged.

Local evidence is retained in `outputs/release-20260925-beta5`, including native,
hardware, launcher, archive, installation, startup, and public download reports.
