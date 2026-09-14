# Lobby compatibility — Arcane Wars 0.3.0-beta.7

The eight Arcane Wars beta helpers embed this x86 native library. They compute an
identity from the applied installation before launching, load the library into
only their own fresh, verified Steam 1.3.72 process, then install five guarded
CALL replacements in a short suspended transaction. No launcher update is needed.
Failure stops the incomplete fresh launch. Stable/Vanilla/Immortals are unchanged.

The module is extracted with a SHA256 check and atomic rename to
`.pawpatch/native/<SHA256>/paws_lobby_compatibility.dll` in the game folder.
This location passed loading in the user's game; AppData loading returned Windows
error 126 on that PC despite identical bytes. Extraction never overwrites a loaded
library. DLL initialization is empty; the explicit installer uses the x86 PEB to
avoid taking the loader lock while other game threads are paused. A native worker
finishes DLL thread notifications before the process is paused, then reports its
result before thread-detach notifications. This avoids the startup lock observed
on the VM. The process is resumed on success and every failure path.

## Identity and wire format

`PWLC1|gameVersion|modId|modVersion|patchVersion|64-character-SHA256`

The digest covers actual game EXE and selected helper bytes, enabled non-language
package manifests and applied gameplay settings. It does not hash every installed
data file: the original native data checks remain enabled. Language choices and
launcher preferences do not participate. No account information, paths or passwords
are sent. This is compatibility checking, not an anti-cheat proof.

The stock host compares the canonical identity before lobby admission. On wrong
version reason 2, the disconnect packet appends its bounded identity. A new receiver
checks length, magic, fields and ASCII limits before showing own/host game, mod and
patch versions in the stock Russian/English dialog. Component or EXE differences
with the same version labels are also rejected, without enumerating individual
files. Missing legacy extensions never invent a host version. Original password,
internal game version, Steam, depot/data checks and simulation code remain in place.

Analysis image base 0x460000; all listed addresses are RVAs:

| Purpose | Call | Original target |
| --- | --- | --- |
| Outgoing version | 0x151092 | 0x07C92F |
| Host expected version | 0x150E40 | 0x07C92F |
| Disconnect reason write | 0x151C8A | 0x149033 |
| Disconnect reason read | 0x1519EF | 0x149046 |
| Disconnect message assignment | 0x151BF3 | 0x023FB6 |

## Build and tests

Use `game/beta7/build.ps1 -CityAssistant -LobbyCompatibility -NativeCompiler <x86-tcc>`
with the existing accepted native source root. `PrepareLobbyBeta7.py` packages all
eight variants in three signed-beta packages while byte-checking preservation of
all other payloads. `FinalizeLobbyBeta7.py` verifies public immutable assets before
promoting beta feeds; it does not publish uploads or push commits itself.

- Protocol parser/format: 225 checks.
- `native_tests.c`: 2,613 checks with the actual 1.3.72 bit reader/writer, cursors
  0–8, disconnect reasons 0–13, truncation and x86 calling conventions. Allocation
  growth alone is replaced with a preallocated test buffer.
- `IdentityTests.cs`: 91 checks covering actual EXE/helper differences, components,
  language independence, cultures, ordering and stale-version refusal.
- `--verify-lobby-beta7`: 18,432 package selections, eight real helper installation
  transitions and uninstall; save preservation and all unrelated channel scopes.
- Existing launcher core suite: 23,085 checks, plus all eight existing native helper
  test suites (city policy revision 15 and fast-transfer revision 2 retained).

`prepare-review.ps1` and `ReviewInjector.cs` are explicit PID-only developer tools,
not distributed. The user accepted the native mismatch dialog in an actual Steam
join: VM beta.4 against PC beta.6 with the temporary hook. Production integration
and additional live outcomes are recorded in the release validation document.
