# Company-badge lighting assets

Seven organizations: Monster, Nationalist, Council, Royalist, Ceyah, Fallen, Default.

The accepted models give only `PlayerColorPlane` a local NiVertexColorProperty
using emissive lighting (SOURCE 0 / LIGHTING 0). The gold frame, type icon,
geometry and other planes keep their original properties. Each model adds 32 bytes.
The matching player-color textures retain 80% of the original shading contrast
(the accepted soft-shading r2 variant), so the colored center still has depth.

Release 0.2.0 packages all seven NIFs and seven TGAs in required `common-ui`.
Beta 7 shipped the textures but omitted the NIFs; local test installations had
the models, explaining the inconsistent appearance between installations.
These common assets no longer depend on enabling extended player colors.

The assets are derived game/mod resources, not covered by the launcher source
license. The game itself is required. Release staging records SHA-256 evidence
and clean-install tests verify all fourteen assets with colors both ON and OFF.
