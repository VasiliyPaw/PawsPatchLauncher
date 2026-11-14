# Native buffer ownership fix — three beta modes

User explicitly requested publication to all betas on 2026-11-13. Targets: Arcane Wars 0.5.1-beta.4 and Vanilla/Immortals 0.5.0-beta.5, Pure runtime 1.3.72-pure.19-beta.5. The same native-allocation graphics DLL replaces the unsafe pool in both product families. Stable and legacy feeds, launcher 1.0.15, experimental bridges/roads and unrelated work are preserved.

Use the project Python with PYTHONDONTWRITEBYTECODE=1. All generated files live under `G:/CodexData/projects/Codex/2026-09-09/paws-patch-kohan-ii-3/outputs/buffer-ownership-release-20261113`; no-launch installer fixtures use `G:/PawBufferPublishQA-20261113`.

Steps: `prepare.py baseline`, `helpers`, `archives`, `catalogs`; `verify.py compiled`, `catalog`, `installers`; `publish.py bundle`, `gate`, `source`, `source-ci`, `release`, `promote`, `readback`, `catalog-ci`. Each action is a separate invocation. Wait for successful exact-commit source CI before release. Verify exact public bytes before promoting feeds; verify canonical main URLs afterward as well as commit-pinned URLs. No games are launched by these scripts.

Baseline is fetched from public main and signatures are checked, not copied from the older shared checkout. Rebuild uses frozen published compiler inputs verified against both source manifests and the actual public package bytes. It changes graphics hash, buffer revision/log, and release identity only. All other embedded resources are compared byte for byte by reflection on 12 compiled helpers. Arcane has 40 built-in tests; Pure is additionally exercised through actual installed preflight for all four variants. Palette checks cover all 12 helpers.

The public asset/source phase uses an isolated Git index and a tree based on current main. It neither moves the shared checkout's HEAD nor modifies its staged changes. Source paths changed remotely since the checkout baseline must be merged explicitly; non-fast-forward publication is refused. Source and feed commits have explicit path allowlists. Existing signing/Git credential helpers are used without copying or printing secrets. Build-input archives exclude keys, game EXE, saves and base RWD archives.

Installer QA uses independent writable copies of files that may be replaced. Only immutable root Data.rwd/Music.rwd use read-only hardlinks; source hashes are verified afterward. Skin archives absent from the compact base fixture are supplied from retained QA inputs and verified against the launcher's stock hashes before use. Early failed setup attempts are retained; they exposed fixture path-length/readonly assumptions and did not launch games or modify the product.

Limit: exact geometry stripes from the user's 46-minute match have not been reproduced. The release fixes two independently demonstrated live D3D9 ownership violations. See `docs/verification-native-buffer-ownership-20261113.md` for the battle, performance measurements and scope.
