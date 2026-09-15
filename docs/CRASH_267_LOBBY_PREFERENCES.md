# Crash 267: retained Arcane Wars lobby in Vanilla

The 2026-09-15 log reports `Cannot create any more major kingdoms` followed by
`Could not create kingdom: kingdom`. Applied settings were Vanilla without Paw's
Patch, German text and Russian speech. The installed modules were only EN base
text, DE text and RU speech. The original Data.rwd matched the clean fixture.

Preferences.rup contained the last multiplayer lobby from Arcane Wars, including
18 Paw's kingdoms and 16 major kingdoms. The original executable has a smaller
kingdom limit. These serialized settings live in Documents/Kohan2, not in the
module installation state, so checking installed files did not catch them.

GameLobbyPreferences runs only before launch, for verified original 1.3.72 and
recognized TGCK v2 / preferences version 19. It replaces incompatible Single- or
MultiLaunchSettings with empty defaults produced by the original game. It also
clears the associated map-generator dictionary. All other chunks remain unchanged,
including general preferences and unknown extensions. The original file is backed
up by content hash beside the preferences in PawsLauncherBackups. Repeat launches
are no-ops. Full Arcane Wars with its runtime keeps its extended kingdoms.

Do not remove required TGCK chunks: the game reports a corrupt preferences file
if MultiLaunchSettings is absent. This was discovered in the isolated prototype;
the final implementation retains all chunks and replaces their payloads.

Validation: 329 regression checks cover mods, runtime off/data-only, single and
multiplayer caches, unaffected settings, backups, unknown formats and idempotence.
The captured crash preferences trigger the final guard; only MultiLaunchSettings
and RMCPreferences change. Engine readback is tested in an isolated user depot.
Match-start acceptance is left to the user, who asked to perform it themselves.
No public release or language package modification is part of this fix.
