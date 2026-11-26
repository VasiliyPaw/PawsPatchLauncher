"""Regression: stock animated parents cannot rotate a bridge-length footprint.

Checks real before/after NIF graphs, particle settings and all emission/fade keys.
This is an asset test; it does not claim a live engine/visual fade test.
"""
import argparse
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import sys
import time
import zipfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-module", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pyffi", type=Path, required=True)
    args = ap.parse_args()
    assert args.out.resolve().drive.upper() == "G:"
    assert args.pyffi.resolve().drive.upper() == "G:"
    sys.path.insert(0, str(args.pyffi))
    time.clock = time.perf_counter
    from pyffi.formats.nif import NifFormat as N

    def read(raw):
        model = N.Data()
        model.read(io.BytesIO(raw))
        return model

    def fields(block, model, skip=()):
        result = []
        for attr in block._get_filtered_attribute_list(model):
            if attr.name in skip:
                continue
            wrapper = getattr(block, "_%s_value_" % attr.name)
            if attr.type_._has_links:
                values = [wrapper.get_value()] if isinstance(wrapper, N.Ref) else list(wrapper)
                result.append((attr.name, tuple(
                    fields(value, model, ("target", "emitter_object")) if value else None
                    for value in values)))
                continue
            result.append((attr.name, wrapper.get_hash(model)))
        return type(block).__name__, tuple(result)

    def particles(model):
        return [b for b in model.blocks if isinstance(b, N.NiParticleSystem)]

    def controller_chain(particle, model):
        result = []
        ctl = particle.controller
        while ctl:
            # Data contains every emission/visibility key, including the last
            # build key. Native stop/fade still acts on the same particle chain.
            result.append((fields(ctl, model, ("next_controller", "target", "data")),
                           ctl.data.get_hash(model) if hasattr(ctl, "data") and ctl.data else None))
            ctl = ctl.next_controller
        return result

    def particle_settings(particle, model):
        return (particle.data.get_hash(model), controller_chain(particle, model),
                [fields(m, model, ("target", "emitter_object")) for m in particle.modifiers])

    def parents(model):
        result = {}
        for node in model.blocks:
            if isinstance(node, N.NiNode):
                for child in node.children:
                    if child:
                        assert child not in result
                        result[child] = node
        return result

    def chain(node, mapping):
        nodes = []
        while node:
            assert node not in nodes
            nodes.append(node)
            node = mapping.get(node)
        return list(reversed(nodes))

    def world_point(node, point, mapping):
        point = list(point)
        for item in reversed(chain(node, mapping)):
            r = item.rotation
            point = [getattr(item.translation, "xyz"[i]) + item.scale * sum(
                getattr(r, "m_%d%d" % (i + 1, j + 1)) * point[j]
                for j in range(3)) for i in range(3)]
        return tuple(point)

    def box_points(emitter, mapping):
        return [world_point(emitter.emitter_object, p, mapping) for p in itertools.product(
            [-emitter.width / 2, emitter.width / 2],
            [-emitter.height / 2, emitter.height / 2],
            [-emitter.depth / 2, emitter.depth / 2])]

    def z_rotation(node, degrees):
        theta = math.radians(degrees)
        node.rotation.set_identity()
        node.rotation.m_11 = node.rotation.m_22 = math.cos(theta)
        node.rotation.m_12 = -math.sin(theta)
        node.rotation.m_21 = math.sin(theta)

    def max_delta(before, after):
        return max(abs(a - b) for x, y in zip(before, after) for a, b in zip(x, y))

    rows = []
    with zipfile.ZipFile(args.source_module) as z:
        for count in range(5, 33):
            for axis in ("x", "y"):
                rel = f"rivers-data/Paws/Bridges/RacialBuild/shadow/work_{axis}_{count:02}.nif"
                before = read(z.read("payload/" + rel))
                after_raw = (args.out / "payload" / rel).read_bytes()
                after = read(after_raw)
                old_particles, new_particles = particles(before), particles(after)
                assert len(old_particles) == len(new_particles) == 4
                assert sum(p.data.num_vertices for p in new_particles) == 140
                assert [particle_settings(p, before) for p in old_particles] == [
                    particle_settings(p, after) for p in new_particles]
                assert fields(before.roots[0], before, ("children",)) == fields(
                    after.roots[0], after, ("children",))
                old_map, new_map = parents(before), parents(after)
                old_vortex = next(b for b in before.blocks if isinstance(b, N.NiNode)
                                  and bytes(b.name) == b"BlackVortex")
                assert isinstance(old_vortex.controller, N.NiKeyframeController)
                old_emitter = next(m for p in old_particles for m in p.modifiers
                                   if isinstance(m, N.NiPSysBoxEmitter)
                                   and m.emitter_object is old_vortex)
                z_rotation(old_vortex, 0)
                old_at_zero = box_points(old_emitter, old_map)
                z_rotation(old_vortex, 90)
                source_rotation_delta = max_delta(old_at_zero, box_points(old_emitter, old_map))
                assert source_rotation_delta > 5, "Before model must reproduce moving long strip"
                fixed_delta = 0.
                # The anchor yaw covers ordinary construction and the late fade
                # with a nonzero bridge rotation. Mutating every stock animated
                # ancestor is stronger than sampling a few times in its curves.
                for anchor_yaw in (0, 17, 90, 233):
                    z_rotation(after.roots[0], anchor_yaw)
                    for particle in new_particles:
                        emitter = next(m for m in particle.modifiers if isinstance(m, N.NiPSysBoxEmitter))
                        assert emitter.emitter_object is new_map[particle]
                        frame_chain = chain(emitter.emitter_object, new_map)
                        assert all(n.controller is None for n in frame_chain)
                        assert all(n.controller is None for n in chain(new_map[particle], new_map))
                        original_points = box_points(emitter, new_map)
                        center = world_point(emitter.emitter_object, (0, 0, 0), new_map)
                        assert abs(center[0]) < 1e-5 and abs(center[1]) < 1e-5
                        for animated_angle in (0, 30, 60, 90, 180, 270, 360, 720):
                            for node in after.blocks:
                                if isinstance(node, N.NiNode) and isinstance(node.controller, N.NiKeyframeController):
                                    z_rotation(node, animated_angle)
                            delta = max_delta(original_points, box_points(emitter, new_map))
                            fixed_delta = max(fixed_delta, delta)
                            assert delta < 1e-5
                rows.append(dict(path=rel, sourceRotationDelta=source_rotation_delta,
                                 repairedRotationDelta=fixed_delta,
                                 particlePhysicsAndSpinUnchanged=True,
                                 emissionAndVisibilityFadeKeysUnchanged=True,
                                 bridgeAnchorYawPreserved=True,
                                 sha256=hashlib.sha256(after_raw).hexdigest().upper()))
    report = dict(passed=True, count=len(rows), variants=rows,
                  testedBridgeYaws=[0, 17, 90, 233],
                  testedAnimatedParentDegrees=[0, 30, 60, 90, 180, 270, 360, 720],
                  totalFootprintChecks=len(rows) * 4 * 4 * 8,
                  lateFadeAssetGraphPreserved=True, liveEngineFadeTested=False)
    (args.out / "shadow-footprint-tests.json").write_text(json.dumps(report, indent=2) + "\n")
    print("SHADOW_FOOTPRINT_REGRESSION_PASS", len(rows), report["totalFootprintChecks"])


if __name__ == "__main__": main()
