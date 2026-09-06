# Noninteractive test errors, 2026-09-07

The user reported occasional memory read/written dialogs while working on the launcher and playing. No current WerFault window or matching launcher/preview crash event was found in the bounded recent-log check, so the source of those specific dialogs is not confirmed. Do not mistake an access violation for proof of low RAM.

Automation processes now opt into process-local `SetErrorMode` flags `SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX`, preserving all other flags. This suppresses standard fatal-error/WER dialogs for that process, not exceptions or exit codes. No registry, Windows-wide reporting policy, security setting, game or already-running user launcher is changed.

- PreviewRenderer and the console test runner opt in before their test bodies.
- The launcher opts in only with `--smoke-test`. Its unhandled WPF test errors write diagnostics/stderr and exit nonzero instead of showing a modal MessageBox. Normal interactive launch behavior is unchanged.
- SmokeLauncher temporarily sets the parent mode before direct redirected child startup so it also covers early failures/older candidate EXEs. It restores its own previous mode in `finally`, retains stdout/stderr, and reports early exit codes. Only its own child PIDs can be closed.
- `--quiet-mode-check` enables the flags and reads them back without creating WPF windows, running package fixtures, or deliberately crashing. This verifies flag setup, not every possible Windows or third-party dialog.

Do not run heavy fixtures in parallel or intentionally provoke native crashes while the user is playing. A screenshot including the executable/window title is still needed if an error appears again.

The previously built local test EXE at `release_workspace_056/combination-fix/win-x64` is not overwritten/re-signed in this turn. Source changes apply to the next build; the updated smoke wrapper also covers prior candidates. No public update was released.

Reference: https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-seterrormode
