# Updating About the patch without a launcher release

Edit `feed/patch-guide.json` as the authoring copy, include it as `patchGuide` in the intended channel payload, and sign the complete feed through the normal publisher workflow. Editing the authoring file alone does not publish a change.

`schemaVersion: 1`, a nonempty `version` and up to 100 uniquely identified entries are supported. Each entry has `id`, `category` (always/optional/beta), `titleRu`, `titleEn`, `bodyRu` and `bodyEn`. IDs use lowercase Latin letters, digits and hyphens. Titles are at most 160 characters; each body at most 12000. All four text fields are required. Text is rendered as plain WPF text, never HTML, XAML or executable commands.

Normal feed checks refresh the guide without reinstalling game files: documentation is intentionally excluded from the game-package fingerprint. Signed cached feeds are verified again for offline reading. The selected pinned feed takes priority over the latest feed. Legacy feeds without a valid guide use the retained pre-Beta-7 built-in catalog.

For a new feature, update the authoring text together with the feature's package and selected release metadata. This is automatic delivery of authored descriptions, not automatic inference from changed game files.

`colorDesyncContinue: true` is a separate game capability. Set it only for a Beta containing `k2_paws_lobby_colors_mp_sync_1372.exe` in the player-colors package. Documentation cannot enable the option.
