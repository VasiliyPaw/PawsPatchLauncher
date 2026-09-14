# Launcher 0.7.6 validation — 2026-09-14

Final process-lifecycle review of 0.7.5 found that the first allowed helper EXE
could prevent discovery of the actual native game. Existing C# helpers wait for
the game to exit and can coexist with k2.exe. The reader now continues after a
null snapshot, unsupported bootstrap or per-process access/exit failure, and
stops at the first valid native snapshot. Only that process retains hash caching.

- Full suite: **16,190 PASS**, including eight process-selection regression cases
  (helper, exited Steam bootstrap, native game, each expected access exception,
  no available game, and stopping after success).
- Native team/color/parser coverage and UI/server verification from 0.7.5 remain
  applicable; no UI or database behavior was changed by this follow-up.
- The production activity migration is already deployed and verified. It is not
  run again. No real account rows or game files were changed for these tests.
- Live two-client Steam lobby/match acceptance remains unperformed; isolated
  tests and disassembly are not claimed as live acceptance.
- The user's open launcher remains untouched.

This version supersedes the immutable 0.7.5 artifact; it is published separately
instead of changing the executable behind an existing release/tag or signature.
