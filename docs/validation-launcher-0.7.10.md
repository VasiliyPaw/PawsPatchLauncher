# Launcher 0.7.10 validation

The installed footer uses the applied mode and enabled base module. Author versions
come from the archived installed release only when its package version matches the
installed module; missing archives fall back to the installed package identity.
Known packaging aliases display Immortals 2.1 and Arcane Wars 0.82.1.8 offline.
Vanilla uses the executable version already read by the compatibility check, not
the version expected by the patch. No extra executable reads, hashes or network
requests are added to rendering or mode selection.

Paw's Patch remains a separate second line when applied. Draft settings, disabled
cached modules and newer catalog offers do not replace the installed version.
Unknown versions show an em dash with an explanatory localized tooltip.

Faction terminology is applied to Russian and English visible labels, tooltips
and accessibility text. The existing `subrace` transport property remains intact
for compatibility with the server and older launchers; no server migration or
game package update is required.

Validation:

- Core suite: **16,501 PASS**, including 92 installed-mod version checks.
- PreviewRenderer build: zero warnings and errors.
- WPF checks: **222 PASS** across Russian and English (32 activity, 16 patch
  version and 63 launcher checks per language).
- All three modes, both patch channels, Paw's Patch on/off, draft selection,
  offline fallback, old installations, missing data, future author releases and
  different actual Vanilla versions are covered.
- The installed footer remains within two lines at the 1050 x 680 fixture size;
  the rendered Russian Arcane Wars footer was inspected visually.
- Existing user launcher and game processes were not stopped or restarted.

Local logs: `artifacts/launcher-0710-core-tests.log`,
`artifacts/launcher-0710-ui-build.log`, `artifacts/launcher-0710-ui/`.
