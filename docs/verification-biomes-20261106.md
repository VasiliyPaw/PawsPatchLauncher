# Arcane Wars 0.4.2 stable / 0.5.0-beta.1 verification

The stable build promotes accepted 0.4.2-beta.11 behavior and does not include the new geometry or UI changes. The beta adds mixed biomes to the core patch, preserving in-game map selection and adding no launcher switch.

- Eight helpers per channel preserve their prior feature composition. Beta helpers add explicit geometry, shared-settings, minimap and company-cap metadata.
- Native geometry payload and HUD payload match the independently tested r2 bytes. Actual relocated x86: 3646 checks; installation rollback/fault paths: 690; UI payload: 27864 prior checks with identical bytes. Both release identity compositions passed 101 checks each.
- Catalog scope: 155714 assertions over 13824 combinations, including patch disabled, languages and component flags. Vanilla, Immortals, base Arcane and launcher packages remain unchanged in each channel.
- Installation matrix: 24 representative combinations (both channels, all six text languages, basic/full options). Final verification additionally invokes the actual release helper's private file verifier without starting a game.
- New keys are installed in the existing main text table for each locale. Root English bytes are unified across overlapping packages and match the helper's integrity guard. Final locale-owner packages (including bot UI at priority 1000) preserve their existing translations and append the new keys. The helper accepts the vetted original and updated Russian display tables.
- Game QA uses a separate marked installation and private Documents/AppData. QA helper changes are confined to process ownership and private profile paths. Original game and saves are not replaced.

Artifacts and exact build/source hashes are stored under `outputs/release-042-050-20261106`. Publication receipts and signed-catalog readback are recorded there after publication.
