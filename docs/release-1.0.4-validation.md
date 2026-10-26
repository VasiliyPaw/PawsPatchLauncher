# Launcher 1.0.4 validation

Publication authorized by the user on 2026-10-26. Source is isolated from the
working tree containing the deferred custom-mod page and delta prototype.
Only background service dispatch, progress coalescing and the ModDB dispatcher
bridge are included, together with an isolated WPF regression fixture.

Previous local accepted-UI candidate: 13 background installation checks passed,
including extraction of 256 files, apply/uninstall/rollback, cancellation,
worker-originated ModDB dialog, and coalescing of 100,000 progress reports.
The original five UI layout/implementation files match the baseline after
line-ending normalization. No real game or VM was run.

Exact release-source test results and public asset/catalog verification are
recorded below after their completion.

## Exact release source

- Console suite: 38,182 checks passed. This excludes unrelated local tests.
- WPF background fixture: 13 passed; 295 input-priority timer ticks, maximum sampled gap 30.3 ms. This is a fixture measurement, not a general latency guarantee.
- Both suites used the isolated release checkout with the original accepted UI.
- No game, VM or recording was started.
