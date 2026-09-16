# Launcher 0.8.3 — local preview

Not published. Based on released launcher 0.8.2 and its public catalogs.

Match participant cards retain their three text lines and 34-pixel avatars while
reducing height from 80 to 64 device-independent pixels. Registered players,
unregistered players and bots keep identical heights. Card gaps shrink from
6 to 4 pixels, with slightly tighter team headings and spacing.

No gameplay, installed game files, account data or published catalogs are changed.
The local executable uses an isolated `test-profile` and public release feeds.

Validation: standalone Windows build succeeded; the existing match-details WPF
scenarios passed 36 checks in Russian and 36 in English, including equal card
heights, long names, missing race/faction data, large rosters, scroll reachability,
profile layering and the local match clock. Measured participant height is 64.
The preview images use synthetic participants and the actual application layout.
