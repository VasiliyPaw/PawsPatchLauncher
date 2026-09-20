# Local Arcane Wars: allied selection economy

Unpublished addition to the existing local test helpers. Uses the original
EconomicImpact row, resource icons and 0.25-second slide animation.

- A live allied primary selection (building, company or unit) displays that
  kingdom's current stock, income, resource balance and capacity through the
  native EconomyBar calculation. Own upper row stays unchanged.
- Own construction/sale/recruitment forecast takes priority while active.
- Own objects, enemies, neutrals, no selection, invalid actors and observers
  do not request another kingdom's economy. On deselection the last displayed
  values slide away; the previous kingdom is no longer queried.
- Native virtual selection/owner and diplomacy queries are used, including
  the existing family/kingdom relationship patches.
- r1 used kingdom-colored numeric text. The user confirmed it works, then
  requested ordinary white numbers; r2 implements that change. Resource icons
  keep their original appearance. The existing fractional KP formatting works
  in this row as well.
- UI-only: no resource, order, AI, alliance, ownership or save changes. Native
  cleanup and destruction clear tracked widget references.

Source: `game/ally-economy`. Build flag: `-AllyEconomy` alongside all current
local flags. Four guarded UI vtable entries, separately protected native code
and writable state. Transactional rollback preserves the payload if rollback
cannot be verified.

Validation: 819 native x86 fixture checks across three ASLR layouts, 303
installation/failure/rollback checks, plus the complete existing helper build
regressions. Eight helper variants are built. Local original executable,
graphics proxy, compatibility DLL, patch state and 1490 TGI files are retained.
Evidence and previous helper backups:
`outputs/ally-economy-20260920` in the outer workspace. The r1 startup log
confirmed installation in game PID 23460. The user's manual acceptance confirms
the visible panel works; the agent did not complete its visual test because the
user was playing and asked not to touch controls. No further game controls or
relaunches are performed for r2.

Previous accepted test changes retained include eight sovereign building slots,
uniform horizontal city-list spacing, and Slaanri enclave guard range 44 /
operational range 46 (formerly 28 / 30), as well as all other current local test
features. Nothing is published by this work.
