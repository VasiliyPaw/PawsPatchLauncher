"""A static bridge footprint independent of stock Shadow vortex animation.

The stock compact effect animates BlackVortex/Dummy01. Parenting bridge-length
boxes under those nodes rotates the entire strip, including emitted local-space
particles. Retain particle spin/color/emission; anchor their coordinate frames.
"""


def stabilize_shadow_footprint(data, nif):
    roots = list(data.roots)
    assert len(roots) == 1 and isinstance(roots[0], nif.NiNode)
    scenes = [b for b in data.blocks if isinstance(b, nif.NiNode)
              and bytes(b.name) == b"Scene Root"]
    assert len(scenes) == 1, "Expected the stock render-property root"
    scene = scenes[0]
    parents = {}
    for node in list(data.blocks):
        if isinstance(node, nif.NiNode):
            for child in node.children:
                if child:
                    assert child not in parents, "Ambiguous source scene parent"
                    parents[child] = node

    def chain(node):
        result = []
        while node is not None:
            assert node not in result, "Cyclic source scene"
            result.append(node)
            node = parents.get(node)
        return list(reversed(result))

    def origin(node):
        position = [0., 0., 0.]
        matrix = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
        scale = 1.
        lineage = chain(node)
        assert scene in lineage
        # The replacement frame is a child of Scene Root; retain height in
        # that coordinate frame rather than applying the bridge anchor twice.
        for item in lineage[lineage.index(scene) + 1:]:
            t = [item.translation.x, item.translation.y, item.translation.z]
            position = [position[i] + scale * sum(matrix[i][j] * t[j] for j in range(3)) for i in range(3)]
            r = [[getattr(item.rotation, "m_%d%d" % (i + 1, j + 1)) for j in range(3)] for i in range(3)]
            matrix = [[sum(matrix[i][k] * r[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
            scale *= item.scale
        return position

    particles = [b for b in list(data.blocks) if isinstance(b, nif.NiParticleSystem)]
    result = []
    for index, particle in enumerate(particles):
        emitters = [m for m in particle.modifiers if isinstance(m, nif.NiPSysBoxEmitter)]
        assert len(emitters) == 1, "Expected one emitter per Shadow layer"
        emitter = emitters[0]
        old_emitter = emitter.emitter_object
        old_parent = parents[particle]
        height = origin(old_emitter)[2]
        animated = [bytes(n.name).decode("ascii") for n in chain(old_emitter)
                    if n.controller is not None]
        frame = nif.NiNode()
        frame.name = ("BridgeFootprintLayer%02d" % index).encode("ascii")
        frame.flags = 16
        frame.translation.z = height
        scene.add_child(frame)
        old_parent.remove_child(particle)
        # Scene Root's inherited render properties and all particle-level
        # controllers remain in use; only the animated parent frame changes.
        particle.translation.x = particle.translation.y = particle.translation.z = 0.
        particle.rotation.set_identity()
        particle.scale = 1.
        particle.world_space = False
        frame.add_child(particle)
        emitter.emitter_object = frame
        result.append(dict(layer=index, height=height,
                           oldEmitter=bytes(old_emitter.name).decode("ascii"),
                           removedAnimatedAncestors=animated,
                           particleCapacity=int(particle.data.num_vertices)))
    assert len(result) == 4
    return result
