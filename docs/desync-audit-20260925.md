# Multiplayer policy audit, 25 September 2026

## Confirmed defects and correction

The shipped r35 callback was extracted from the beta.3 helper and exercised in
x86 emulation. With an identical company/world, removing the local strategic AI
player (as on a network client) changed path LOS from false to true. The native
AI fibers exist on the host only in all three supplied session logs.

1. `routing.c` used `ai_for_kingdom` to decide whether to apply danger costs.
   r36 uses common session player records: bot flag `+0xc`, assigned live kingdom
   `+0x28`, exact native player vtable, bounded session list. This is the same
   native ownership mapping used by the lobby and activity reader. Missing,
   duplicate, malformed and cyclic records retain native routing. Human paths
   and disabled AI improvements retain native behavior.
2. The same path callback bypassed danger for a local strategic attack goal.
   This host-only bypass is removed. Explicit hostile query targets and actual
   company/member combat states still bypass danger on all peers.
3. Common queued/direct recruitment admission (sites `21CA36`, `21C938`) used
   local AI demand/cache data to veto the native return value. These callbacks
   now only observe native admission. Supply/builder limits are checked in AI
   selection and immediately before final AI budget reservation (mode 29),
   before the command is created. Clients neither plan AI nor rerun its policy.

The new differential regression executes compiled x86 callbacks/wrappers with
and without a local AI controller, with differing local strategic goals,
bot/human ownership, hostile targets, supply counts and native admission results.
Builder execution covers human, Haroun and Undead recipes. Three relocated image
bases, native upper return bits, register preservation and write bounds are
checked. Engine service stubs remain explicit; this is not a played network test.

## Related audit

- Other AI callbacks change host planning/goals or send native commands. The
  final hero filter is inside native AI goal call site `1D5937`, not common
  simulation admission. Recruitment count mirrors and builder demand caches
  remain inside host planning after removal from mode 7.
- Common child-construction validation uses replicated actor identity,
  generation, ownership, center and body state. Regional empty/empty CV handling
  depends on its numeric native inputs, not a local AI controller.
- Company position recovery, exhausted-state recovery and lair survivor hooks
  use simulation components/events; no wall clock or local player/AI ownership
  decision was found in their simulation branches. Existing relocated native
  and transaction tests are included in the complete helper build.
- Foundation allocation orders candidates by registered actor ID, does not
  compare process addresses to break ties, and preserves the native random
  selection count. It does not use an OS RNG or wall clock.
- City assistant wall-clock scheduling and preferences submit ordinary native
  command requests. The reviewed automatic militia path uses TellActorCommandOrder
  validation/send, not a direct world mutation. Temporal proximity to the first
  desync is insufficient to call it the cause.
- The previously fixed custom-color decree checksum boundaries are retained.
  No checksums were disabled/reset and no native error suppression was added.

These are bounded code/fixture conclusions, not proof that every possible
multiplayer fault is excluded.

## Evidence limit and acceptance

All three players reported the same beta.3 compatibility identity and matching
runtime hashes. First native divergence was within the first game second; the
first captured route report was at game time 206.0625. Therefore the confirmed
routing bug does not establish that first trigger. The final recruitment defect
is independently reproducible, but the first differing command is not present
in paired current native sync histories from the supplied archives.

The existing optional “continue after desync” mode suppresses native failure
handling; it does not repair divergent worlds. A new two-machine match with
identical beta.4 packages is required: start, concurrent hiring, builder travel
past guards and combat. For first-error investigation use native desync handling
and retain both peers' fresh diagnostics. No two-machine acceptance is claimed.

Detailed local evidence: `outputs/desync-20260925/diagnosis.md` and the shipped
payload differential reproduction. The release changes runtime helpers only;
game definitions, save serialization, launcher and stable channel are unchanged.
