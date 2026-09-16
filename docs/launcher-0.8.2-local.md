# Launcher 0.8.2 — local test

Historical local validation record, based on the released 0.8.1 launcher.
These changes were published in [0.8.2](release-0.8.2.md) on 2026-09-16.

## Changes

- Open dropdowns consume wheel input outside their list and stop an already running background scroll animation. Long lists still scroll internally, including safe handling at either end. Closing a popup restores normal page scrolling.
- The common boundary covers the interface language, game text/speech, release chooser, history filters and context menus. The reported reproduction was the interface-language selector; a matching reproduction in text/speech was not claimed.
- The ComboBox template exposes its standard `PART_Popup` and uses `MaxDropDownHeight`.
- Failed Discord attachment requests with an expired signed URL show a localized explanation and ask for a fresh link. Expiry requires a 403/404 response and the expired signature on an exact Discord attachment host/path. Successful responses and cached images remain usable. Other failures retain retry, and failed URLs remain selectable/copyable.
- Reopening the same player card during its closing animation now cancels the previous dismissal. Refreshing an already interactive card still avoids reopening it.

## Validation

- Core suite: 26,435 checks passed, including signed URL preservation, expired versus future/invalid signatures, unrelated hosts, HTTP errors and successful responses despite an old timestamp.
- Actual offscreen WPF popup fixtures: 49 checks across seven selectors, short/long lists, wheel directions and bursts, edge handoff, capture targets, existing inertia, Escape, selection/reopening, two context-menu styles, unrelated windows and unload.
- Media layout/error fixtures: 33 checks in each of ru/en/uk/cs/de/fr. General social/media interaction fixtures also passed in ru/en (54 checks each; that older fixture has ru/en-specific text assertions).
- Motion (35) and smooth scrolling/profile reopen/modal blocking (33) checks passed after fixing the same-profile dismissal race. Chat picker interactions (62) and friend-settings UI scenarios (639) also passed.
- Real read-only media probe: the user's refreshed Discord URL loaded through the production `ChatMedia` transport and WPF PNG decoder: 1,313,066 bytes, 756×1094. Although its filename ends in `.gif`, the supplied content is a single-frame PNG. No media file or signed URL is stored in this repository.
- Game execution is not required for these launcher changes. No game was launched and the user's running launcher was not restarted.

The delivered executable has a `launcher.test-mode` marker and its own `test-profile` directory. The game directory is the normal installed game, not another game copy; applying game settings from the test launcher modifies that selected installation.
