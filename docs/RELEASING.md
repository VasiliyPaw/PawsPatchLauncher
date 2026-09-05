# Release process

1. Build and test the launcher locally.
2. Upload Paw's Patch module archives to the matching GitHub Release.
3. Build `feed/stable.json` with final immutable asset URLs, sizes and SHA-256 hashes.
4. Sign the feed locally with `PawsPatchPublisher`. Never copy the private key to GitHub.
5. Commit and push only the signed `feed/stable.json` envelope after every referenced asset is available.

Before publishing either feed, run `tools/VerifyPublishedFeeds.py feed/stable.json feed/beta.json` to anonymously download every referenced asset and compare its size and SHA-256. Checking release existence alone is not sufficient. Keep module asset release versions independent from the launcher version.

Retain signed Beta snapshots under `feed/history/` and reference them with `previousReleases` in the current signed manifest. Preserve their original signatures. Verify that every historical asset remains available before advertising it.

Experimental work is published to the independently signed `feed/beta.json`. Promote a tested package to Stable only by rebuilding and signing the Stable payload; never edit a signed envelope by hand.

Keep the launcher metadata current in both feeds. Running launchers poll only their selected channel and show a self-update button when its signed launcher version increases. Package changes are detected independently from launcher changes.

The Arcane Wars base archive belongs to Darquan Mortis. Prefer an author-controlled download or obtain explicit redistribution permission before mirroring it as a release asset. The public launcher repository contains no Arcane Wars game data.
