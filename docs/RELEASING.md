# Release process

1. Build and test the launcher locally.
2. Upload Paw's Patch module archives to the matching GitHub Release.
3. Build `feed/stable.json` with final immutable asset URLs, sizes and SHA-256 hashes.
4. Sign the feed locally with `PawsPatchPublisher`. Never copy the private key to GitHub.
5. Commit and push only the signed `feed/stable.json` envelope after every referenced asset is available.

Experimental work is published to the independently signed `feed/beta.json`. Promote a tested package to Stable only by rebuilding and signing the Stable payload; never edit a signed envelope by hand.

The Arcane Wars base archive belongs to Darquan Mortis. Prefer an author-controlled download or obtain explicit redistribution permission before mirroring it as a release asset. The public launcher repository contains no Arcane Wars game data.
