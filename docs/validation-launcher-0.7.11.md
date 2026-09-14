# Launcher 0.7.11 validation

## Scope and cause

- The profile avatar template painted its ring after the avatar content, covering the status dot. An `IsKeyboardFocused` trigger also kept that hover ring visible after the preview restored focus. The ring now paints behind the avatar/status content; hover and keyboard focus use separate visuals. Focus restoration remains intact.
- Pure-mode help inspected `_channel`, which may represent a cached installation. Hover tooltips were populated only during language initialization. Help now shares the guide's current-channel/archive selection and refreshes when compatibility/component controls refresh. Equal tooltip text is left untouched to avoid unnecessary tooltip updates.
- Canonical v2 stable guides contain `dvorak` for Vanilla and Immortals (Paw's Patch 0.1.1). Beta guides contain `dvorak` and `fast-save-transfer` (0.2.0-beta.1). Game packages and these signed guide entries require no changes.

## Automated checks

- Core suite: **16,501 PASS**.
- PreviewRenderer build: **0 warnings, 0 errors**.
- Avatar preview: **41 PASS per language**, Russian and English. Includes actual WPF hover/focus triggers, rendered status-dot pixels, focus after close, outside click, Escape, cache reuse, identity changes, delayed avatar reads and parent/profile cleanup.
- Per-mod channels: **55 PASS per language**, Russian and English. Includes both mods and channels, old installed catalog versus current guide, clicked help versus hover text, absent Arcane Wars credits, incompatible-game restrictions and explicit historical selection.
- Total targeted UI assertions: **192 PASS**. The existing generic layout/transfer checks also completed in the channel fixtures.
- Visually inspected the rendered Russian profile with the hover ring and status dot.

## Boundaries

All UI fixtures ran offscreen with isolated synthetic profiles and local feeds. The user's launcher and game were not restarted, and no live social account was modified. This release changes launcher presentation/documentation selection only; it does not address the separately investigated game crash or change city automation.

Release CI and published asset/catalog verification are recorded separately in `work/launcher-release-0711`.
