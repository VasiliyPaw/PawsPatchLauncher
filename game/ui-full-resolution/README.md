# Full-resolution approved UI artwork

Arcane Wars 0.6.0-beta.4 and Vanilla/Immortals 0.5.0-beta.8 use the approved HD artwork at its original resolution. Most icons are 1254x1254; three are 1024x1024 and one is 1402x1254. Seven 5016x1254 faction masters retain lossless exact left/right 2508x1254 and center 627x1254 crops. No source image is resized while exporting. PNG bytes are preserved; TGA exports preserve exact RGBA pixels. Existing widget dimensions, filtering and native gameplay modules are unchanged.

The UI packages contain 645 icon paths in an image-only paws-hd-ui/ depot and 63 existing faction/spectator frame paths. Generic, 800 and 1280 resource paths are provided. The depot mounts after the existing depots, without the flag that previously prevented the override. Custom RWD startup composition continues through the launcher's existing mechanism. Removing the UI module restores startup and the previous textures through ModuleInstaller.

Accepted artwork provenance and SHA-256 hashes are in image-export.json. Payloads are distributed in the immutable common-ui and pure-beta-common release assets, not Git. Build-input bundles contain the exact compiler inputs and a portable rebuild script; only the managed version identities changed. Native code, day-cycle settings, gameplay TGIs and terrain archives are retained from the preceding betas.

Live 2560x1440 and Direct3D texture-upload evidence comes from the accepted Arcane candidate. Other race masters were checked by dimensions and exact pixels. The release verification distinguishes installer/preflight checks from in-match visual acceptance. No new multiplayer match is claimed for this image-only update.
