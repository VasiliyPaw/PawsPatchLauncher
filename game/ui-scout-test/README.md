# Private UI and reconnaissance candidate

Local test version `0.5.0-ui-test.1`, Kohan II 1.3.72 / Arcane Wars 0.82.1.8.
These files are an isolated prototype; they do not modify release build inputs.

`build.py --out <new-directory>` rebuilds one private helper from the hash-pinned
no-hotjoin beta.4 source snapshot and builds normal/QA native plugins with TCC.
It extends the existing HUD primary-view layout hook to recognize the anonymous
resign widget by its native vtable. The remaining changes live in `runtime.c`.

Run `test_native.py --build <directory>` and `test_hud.py --build <directory>`.
The first executes the compiled x86 callbacks and generated dispatch in Unicorn;
native command transport is explicitly stubbed. The second verifies the actual
HUD bytes embedded in the rebuilt helper. Neither starts a game.

`prepare.py --build <directory> --out <new-directory>` prepares a private playable
copy, localized in Russian, with private Documents/AppData. Launch through its
`Start-Test.cmd`. Its `Mods` contains only the normal plugin, with no QA bridge.
The helper detects running games by full executable path, so other QA copies
are not stopped or attached to.

`qa.h`, `live.py` and `inspect_live.py` support a separately owned local live test.
The inspector checks the process's full executable path before reading it.
`verify_package.py` checks final hashes, absence of QA exports and recorded live
recon intervals; it starts no processes. `research.py` is the extraction and
disassembly scratchpad, not a build dependency.

See `docs/verification-ui-scout-20261109.md` for results and known test limits.
