# Launcher 0.7.9: participant identity, race and layout

The reported match published a fresh twelve-player roster (one human, eleven
bots), but its authenticated owner's `self` key was null. A read-only production
query confirmed this before the change. No nicknames or single-human assumptions
are now used as identity shortcuts: native `manager +0xc` is the player wrapper,
whereas the previous reader compared it with the distinct network-peer pointer.
See `game-activity-native-identity-races-20260914.md` for disassembly and emulation.

Race/subrace use native Nation/Faction definition IDs. Null lobby choices are
independently Random. Matches use actual kingdom definitions rather than the
lobby template; unavailable fields remain unknown. Russian labels were checked
against the shipped Russian localization. The viewer's launcher language selects
the displayed labels.

## Completed validation

- Launcher build: zero warnings and errors.
- Core suite: **16,409 PASS**, including 120 native identity/race checks and
  account-transport roundtrips, invalid input and legacy-server fallback.
- Isolated PostgreSQL suite: **5,272 PASS**, including 123 activity checks.
- WPF activity/participant/avatar checks: **170 PASS** across Russian and English.
  Twelve- and sixty-four-player lists, random lobby values, profile/avatar
  navigation, scrolling, asynchronous close/reopen and old clients are covered.
- Rendered Russian twelve-player and random-lobby previews inspected visually.
- Server migration applied atomically through the authenticated Supabase SQL
  editor on 2026-09-14. Expected old validator MD5 was
  `46fe7efeb2f9afa3fc0a3ed486c09be9`; tested new MD5 is
  `b01105abadb6bdb525395136b46be7b9`. Owner, privileges, security mode, search path,
  language and volatility were checked unchanged. A separate read-only query
  returned **10/10 true** for the new contract and access checks.

No production account, friendship, message or presence row was used as a test
fixture. No existing launcher was stopped or restarted. No new live two-client
multiplayer session was conducted: native-layout evidence and deterministic
tests do not claim to be that acceptance check. The publishing player must also
update the launcher before the new identity and faction fields appear remotely.

Local evidence: `artifacts/activity-079-core-tests-final.log`,
`artifacts/activity-079-ui-build.log`, `artifacts/activity-079-ui/`, and
`artifacts/game-participant-factions-database.log`.
