# Local foundation distribution, 2026-09-21

The AW `SettlementCamps` actor group previously chose ordinary settlement camps
and foundation camps with weights 2 and 1. `balanced_placement=true` spread the
combined set; it did not distribute each type separately. The existing standalone
`FoundationCamps` template had range 0,0 and was absent from every random-map variant.

The local data overlay enables that separate balanced group in all five variants
(arctic, cursed, desert and both temperate variants). Its range is 20% of
the old combined range (0.8,1.6), and ordinary settlement camps use 80% (3.2,6.4).
Both keep area_factor=1.4. Native integer rounding can change the total by one;
actual placement remains subject to terrain and valid-space checks.

Foundations run after starting cities/random cities and before settlement camps.
They are therefore not restricted to whatever gaps the more numerous camps leave.
Both groups retain 128-unit configured separation from starting/random cities;
settlement camps also repel the already placed foundations. All 16 later group
restrictions that previously referred to the mixed group now refer to both groups
with the same original distances. No forward reference to an unplaced group is
added. Ownership, camp contents, defenders, terrain settings, UI sliders and save
records are unchanged.

`prepare.py --game <installed AW root> --out <new directory>` prepares five files
and before/after SHA-256 manifest without editing the game. The checked-in `data`
directory is the prepared local overlay. The matching five startup hash guards
in beta7/ReleaseStartup.cs and RandomMapBundle.cs must travel with these files.
Do not merge these files into the optional AI data module: map generation applies
regardless of the AI toggle and also affects human players.

Native evidence, mapped 1.3.7.2 image base 0x860000:

- RVA 05625C parses balanced_placement into actor-group +58.
- 259098 branches per actor group; 2590A3 constructs a fresh balancer and
  2590B4 calls 258308 with that group's definition.
- 258389..25839B truncates the scaled requested count; 2583C8..258402 computes
  separation from map width / (floor(sqrt(count)) + 1).
- 2586D8 seeds the group's positions and selects object types from its weighted
  table. The shared balancer consequently cannot prevent type clustering.
- 2585C2 uses cross-group repulsion with max(configured distances, current
  balancer separation). Configured distances are not strict spacing guarantees.

Validation distinguishes data/ABI tests from an actual generated-map sample.
This improves spatial distribution, not exact per-team mirroring. Only newly
generated maps change; loading a save does not regenerate or relocate its sites.
No release has been published by this local preparation.

## Requested-count hook (revision 1, retained)

The 2026-09-21 new-map log requested and placed 19 settlement camps and 15
foundation camps despite the installed 80/20 ranges. The loaded definitions
matched the overlay; saved RMC values still contained older midpoints. Therefore
the ranges alone are not a guarantee of the requested final distribution.

The optional FOUNDATION_COUNTS helper module hooks RVA 25839B, after native
scaling/truncation and before spacing calculation. For the two named balanced
camp groups it reads the current creator's effective value table (+64/+68) and
profile actor groups (+74/+78), reproduces both native integer counts and splits
their combined total: foundations = nearest(total / 5), settlements = remainder.
Both groups use the same native area scale; group order does not affect the split.
It adds no RNG calls and preserves the native total. Random cities and enclaves
are separate groups and are not included in this camp ratio. Placement can still
fail when terrain lacks valid space; generation logs distinguish requested from
actually placed counts. Unknown layouts/groups retain their native count.

The single hook is guarded against the saved 1.3.7.2 image, installed while the
game is suspended, and transactionally rolled back on failure. It preserves
registers, flags and floating-point state before executing displaced instructions.
It is independent of AI options. Existing saves/maps are never regenerated.
test_counts.py executes the compiled relocated x86 wrapper with explicit native
area-scale stubs. TransactionTests.cs injects allocation, write and rollback
failures. Neither suite claims a played/generated game map.

## Actual camp distribution (local revision 2)

The next live map requested 38 settlement camps and 9 foundation camps, but
only 27 and 9 were successfully placed. Revision 2 retains the requested-count
hook and classifies the final successfully placed random-camp placeholder pool
at the successful generation epilogue (RVA 255E09). Foundations are rounded to
the nearest fifth of that pool; remaining sites become settlement camps.

Farthest-point sampling spreads the foundation subset over the pool: first near
the centroid, then farthest from the nearest selected foundation. Ties preserve
registry traversal order. Coordinates, native spacing, existing objects and
definitions are unchanged. This is global spacing, not mirrored team quotas.

When the stock initializer resolves each placeholder (call site RVA 247A27),
the selector supplies its chosen family's weighted table to the original
routine. Stock RNG, concrete camp replacement and marker creation still run.
Ready cities and enclaves are separate groups. Existing maps and saves are not
regenerated; the plan is only active for the newly generated world and consumes
each matching actor ID once. Failed generation clears it.

All three sites are guarded and transactionally installed/rolled back together.
test_final.py executes the native planner and wrapper at two bases, tests actual
pool sizes, spatial coverage, engine-memory immutability, lifecycle and wrapper
ABI. Definition lookup and weighted selection boundaries are explicitly stubbed;
these checks do not replace a fresh in-game generation test.

### Writable state correction (2026-09-21, log-375)

The initial revision-2 installer protected the entire allocation as RX. The
first `FinalPlan.ready` write at payload offset 0x17F2 then faulted at state+4.
Only [cave, cave+DataOffset) is now RX; the separate page-aligned state remains
RW and is explicitly zeroed before any hook is installed. Native payload and
generation rules are unchanged. Transaction tests track page permissions;
the native emulator reproduces the old exact write fault before exercising
the planner and selector with RX code and RW state.
