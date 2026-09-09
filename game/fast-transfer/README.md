# Built-in native save transfer — R2

Included unconditionally with Beta city policy in all eight release helpers. This is the user-accepted R2 tuning, not the later aggressive experiment: a 1200-byte file-stage budget and at most 16 packets per peer per send pass. The earlier host-PC/client-VM run transferred a roughly 1.6 MB save in about nine seconds and successfully entered the game. That is prior manual evidence, not a promised network speed or a new multiplayer test of this release.

The game still detects missing/different lobby saves and handles requests, acknowledgements, retries, reconstruction and native replacement. No launcher friendship, cloud storage or approval card is involved. The stock block size, wire format and save format remain unchanged. Both endpoints should use matching Beta and gameplay settings.

`prepare_guards.py` extracts 15 exact instruction regions (1815 bytes) from the local verified 1.3.72 analysis image. The release installer checks them and fresh process identity before patching. Only verified file-stage paths are tuned; normal gameplay packet handling stays native. A guard mismatch fails startup instead of patching an unknown build.

`FastTransferTests.cs` runs 663 managed guard/layout checks. `test_native.py` runs 8421 x86 emulation checks on emitted hooks and native packet-type gates. Socket/file I/O and real packet loss are not emulated. Production helper self-tests do not export files; the standalone test build exports its payload into a dedicated test directory.

Built through `game/beta7/build.ps1 -CityAssistant`; see [release validation](../../docs/release-030-beta2-validation.md).
