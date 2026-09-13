# Unified changelog (local candidate, 2026-09-10)

The Home history has independent subject, source and patch-branch filters. Subjects are Launcher, Vanilla, Immortals and Arcane Wars. Sources are all changes, the author's mod (the original game for Vanilla), and Paw's Patch. Patch branches are Release, Beta or both. Launcher history and author-mod history have no Paw's Patch branch selector.

The initial history follows the selected game mode and its remembered patch channel. Browsing another history does not select a game mode, change its channel, request a package, or alter components. Identical notes from both patch branches display once with both branch labels. Long cards expand and collapse with animation.

Unread state is stored per subject, source, branch and entry. A changed entry body is unread again. Existing read markers migrate; guides without dated release notes are version overviews and do not create unread notifications. The Home badge follows launcher notes plus the selected mode's notes on its selected patch branch. Dropdowns show the other subjects' unread notes without creating game-update offers.

## Feed authoring

Existing signed `ChannelManifest.changelog` entries use `category: "launcher"` or `category: "patch"`. For patch or mod entries, explicitly set `mods: ["vanilla"]`, `["immortals"]` or `["arcane-wars"]`; omitted scopes retain the legacy Arcane Wars meaning.

Author releases can be supplied as `category: "mod"` with an explicit `mods` scope, or in a corresponding `modGuides[].changelog` array. Each guide entry has `version`, `publishedAt`, and bilingual `title` and `body` objects with `ru` and `en`. Use an empty `publishedAt` when the source does not establish a release date. The guide supplies its mod scope; no launcher patch-channel meaning is assigned to author releases.

Guide histories are limited to 200 entries. Version and date strings are limited to 80 characters, each localized title to 200, and each localized body to 40000. Signed feed data is never rewritten while rendering. Existing signed-feed validation and cache remain in use, so approved guide/history edits can be delivered without a launcher executable update.

The bundled Arcane Wars guide includes the author's supplied 0.82.1.4, 0.82.1.6 and 0.82.1.8 release notes in Russian and English. Original publication dates were absent and were not invented. The Immortals 2.1 guide supplies a version overview; this is not presented as a complete chronological release history. Built-in guide notes are used offline and as a fallback for the same guide version.

## Validation

- Main suite: 10326 assertions, including 98 timeline assertions.
- Timeline WPF checks: 20 Russian and 20 English assertions, with shared typography, transfer-panel and layout checks.
- Related Russian refinement checks: 131 assertions.
- The local test launcher is built with a separate test profile and signed local feeds; no public release or game package was changed for this history update.

Native visual acceptance and the precise executable hash are recorded in `outputs/launcher-history-review` in the surrounding workspace.
