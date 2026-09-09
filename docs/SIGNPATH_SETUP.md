# Activating SignPath signing

Status: prepared, not approved or active. Existing downloads remain unsigned.

1. Apply at <https://signpath.org/apply>. Supply the maintainer's chosen name and
   contact email. Describe this small, newly released project truthfully and link
   the repository, releases, CI, privacy policy and code signing policy. Disclose
   separately downloaded game/mod content outside the requested signature.
   The maintainer must review the required Code of Conduct/privacy consents.
2. SignPath decides admission. Verify GitHub and SignPath MFA, then connect the
   repository using their approved integration. Restrict production signing to
   trusted release sources and require manual maintainer approval in SignPath.
   Do not enable production signing for arbitrary forks or pull requests.
3. Import `.signpath/launcher-artifact.xml`. It accepts one executable inside the
   GitHub artifact ZIP and restricts product/version metadata. Validate it in
   SignPath; local XML parsing cannot replace their schema/server validation.
4. Configure repository secret `SIGNPATH_API_TOKEN` for the approved submitter and
   repository variables `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`,
   `SIGNPATH_SIGNING_POLICY_SLUG`, `SIGNPATH_ARTIFACT_CONFIGURATION_SLUG`,
   `SIGNPATH_EXPECTED_PUBLISHER`. The publisher must be the **exact certificate
   Subject** from SignPath, not a guessed or partial name.
5. Manually run **Publish launcher** with `request_signing: true`. This builds,
   signs, verifies and uploads artifacts without publishing a release or feeds.
   Approve the request in SignPath. Verify the final manifest says `Valid`, shows
   the correct publisher and a timestamp, and that ZIP/standalone EXE match.
6. Test the signed build on clean Windows and verify launcher update/rollback.
   SmartScreen reputation warnings may still appear; do not promise otherwise.
7. Before the first signed public release, set `SIGNPATH_ENABLED` to `true`.
   All subsequent tag builds then require successful signing. Keep it enabled.
   Until activation, existing tag builds remain explicitly unsigned so onboarding
   does not interrupt existing releases. They emit a warning and truthful manifest.
8. Use a **new version/tag**, not v0.6.4. Add release notes and publish the tag.
   Pass the verified **signed CI executable** to `PrepareLauncherOnlyRelease.ps1`
   so the new feeds use its post-signing size/hash. Preserve game/module identities.
   Never substitute an old unsigned local build via `PublishLauncherRelease.py`.
9. Update the current-status sections in README and CODE_SIGNING after the signed
   release is actually public. Do not claim SignPath endorsement before approval.

## Local verification

```powershell
dotnet publish src/PawsPatchLauncher/PawsPatchLauncher.csproj -c Release -r win-x64 --self-contained true -p:IncludeSourceRevisionInInformationalVersion=false -o artifacts/signing-build
./tools/TestLauncherSigning.ps1 -BuildDirectory artifacts/signing-build -WorkDirectory artifacts/signing-checks
```

Local checks exercise unsigned rejection, required settings, version mismatch,
final digests and ZIP identity without changing the trust store. A real signature,
publisher/timestamp validation and SmartScreen behavior remain external checks
requiring the approved service. Source signing policy and integration reference:
<https://signpath.org/terms>, <https://docs.signpath.io/trusted-build-systems/github>.
