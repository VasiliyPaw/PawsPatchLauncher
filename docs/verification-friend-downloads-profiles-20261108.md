# Friends during downloads, full profiles and directory discovery

Subsequently released on 2026-11-09 as launcher 1.0.11. See
`verification-launcher-1.0.11-20261109.md` for production deployment and publication.
The local-only status below describes the earlier preview snapshot.

Local changes on top of launcher 1.0.10. Not published: no feeds, tags, server
functions or production migrations were changed. The new profile migration is
prepared locally in `20261108020000_unblocked_player_profiles.sql`.

## Behavior

- Accept, decline, cancel requests, remove/block/unblock and profile friendship
  actions no longer depend on the game download/install busy flag. Social
  confirmations preserve the installer operation and its progress.
- Declining or cancelling a configuration/save offer is also available during
  installation. Applying configurations, receiving saves and other shared file
  operations still wait for the active operation; acceptance explains this.
  Sending offers/broadcasts and signing out retain their existing restrictions.
- Incoming/outgoing requests have separate count tabs, readable identities,
  larger buttons and adaptive narrow cards. Screenshots use the actual WPF UI
  with isolated fictional players, not production accounts.
- Adding a player from a profile sends the request immediately and retains the
  open profile. Sparse relationship responses preserve its full configuration.
- Signed-in users can view full nonfriend profiles, settings and shared activity.
  New authenticated endpoints check blocks in either direction. A block shows
  an explicit explanation and invalidates the visible profile on refresh.
  Messages and file transfers retain friendship requirements; guests see basic
  cards. Participant matching still strips room/self metadata and retains its
  existing ambiguity rules. Privacy documentation was updated.
- The online counter has a small amber exclamation mark until its first opening.
  `OnlineDirectorySeen` is immediately saved in the ordinary per-user
  `%LOCALAPPDATA%/PawsPatchLauncher/settings.json`, independent of release version,
  language, account and executable location. The existing updater replaces the
  executable and preserves this settings directory. Settings serialization and
  construction of a fresh window from saved settings verify the hidden state.

## Verification

- Release build: passed, no errors.
- C# suite: 38,418 assertions passed.
- Isolated PostgreSQL/WASM migration/API checks: 12,547 passed, including full
  nonfriend configuration/activity, guest denial, both block directions and
  unchanged private messaging permissions. No production mutations.
- New download/profile/discovery UI fixture: 35 checks passed in Russian and
  35 in English; uses mocked authenticated transport and mutations.
- Community UI: 120 passed, including first-open persistence and a fresh window.
- Game participants: 18 passed. Social action eligibility: 19 passed.
- Background installer: 13 passed through real isolated download/extraction,
  verification, commit, rollback and cancellation; UI max dispatcher gap 28.5 ms
  in this run. This complements the social fixture's active-operation checks;
  no live two-account/game acceptance test was performed.
- Visually reviewed Russian incoming/outgoing, narrow cards, full nonfriend
  profile and discovery badge before/after screenshots.
- Two broader legacy UI suites stop at existing assertions: LayoutRefreshChecks
  reports “Friends title wraps at minimum width”; SocialHubChecks reports
  “profile components names/order differ from tab”. Both exact failures were
  reproduced from an isolated archive of HEAD/1.0.10 without these changes.
  They are not counted as successful checks above.

Evidence and screenshots:
`../../outputs/friend-requests-review-20261108/` from the project root above this
checkout. Logs are in the same top-level outputs directory, named `friend-*`.
The isolated baseline source and failure logs are retained there as well.
