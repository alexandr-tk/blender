# SPDX-FileCopyrightText: 2021-2023 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

import pathlib
import sys
import unittest
import tempfile

import bpy

args = None


class AbstractNodeGroupInterfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testdir = args.testdir
        cls._tempdir = tempfile.TemporaryDirectory()
        cls.tempdir = pathlib.Path(cls._tempdir.name)

    def setUp(self):
        self.assertTrue(self.testdir.exists(),
                        'Test dir {0} should exist'.format(self.testdir))

        # Make sure we always start with a known-empty file.
        bpy.ops.wm.open_mainfile(filepath=str(self.testdir / "empty.blend"))

    def tearDown(self):
        self._tempdir.cleanup()


class NodeGroupInterfaceTests:
    tree_type = None
    group_node_type = None
    # Tree instance where node groups can be added
    main_tree = None

    def make_group(self):
        tree = bpy.data.node_groups.new("test", self.tree_type)
        return tree

    def make_instance(self, tree):
        group_node = self.main_tree.nodes.new(self.group_node_type)
        group_node.node_tree = tree
        return group_node

    def make_group_and_instance(self):
        tree = self.make_group()
        group_node = self.make_instance(tree)
        return tree, group_node

    # Utility method for generating a non-zero default value.
    @staticmethod
    def make_default_socket_value(socket_type):
        if (socket_type == "NodeSocketBool"):
            return True
        elif (socket_type == "NodeSocketColor"):
            return (.5, 1.0, .3, .7)
        elif (socket_type == "NodeSocketFloat"):
            return 1.23
        elif (socket_type == "NodeSocketImage"):
            return bpy.data.images.new("test", 4, 4)
        elif (socket_type == "NodeSocketInt"):
            return -6
        elif (socket_type == "NodeSocketMaterial"):
            return bpy.data.materials.new("test")
        elif (socket_type == "NodeSocketObject"):
            return bpy.data.objects.new("test", bpy.data.meshes.new("test"))
        elif (socket_type == "NodeSocketRotation"):
            return (0.3, 5.0, -42)
        elif (socket_type == "NodeSocketString"):
            return "Hello World!"
        elif (socket_type == "NodeSocketVector"):
            return (4.0, -1.0, 0.0)

    # Utility method returning a comparator for socket values.
    # Not all socket value types are trivially comparable, e.g. colors.
    @staticmethod
    def make_socket_value_comparator(socket_type):
        def cmp_default(test, value, expected):
            test.assertEqual(value, expected, f"Value {value} does not match expected value {expected}")

        def cmp_array(test, value, expected):
            test.assertSequenceEqual(value[:], expected[:], f"Value {value} does not match expected value {expected}")

        if (socket_type in {"NodeSocketBool",
                            "NodeSocketFloat",
                            "NodeSocketImage",
                            "NodeSocketInt",
                            "NodeSocketMaterial",
                            "NodeSocketObject",
                            "NodeSocketRotation",
                            "NodeSocketString"}):
            return cmp_default
        elif (socket_type in {"NodeSocketColor",
                              "NodeSocketVector"}):
            return cmp_array

    def test_empty_nodegroup(self):
        tree, group_node = self.make_group_and_instance()

        self.assertFalse(tree.interface.items_tree, "Interface not empty")
        self.assertFalse(group_node.inputs)
        self.assertFalse(group_node.outputs)

    def do_test_invalid_socket_type(self, socket_type):
        tree = self.make_group()

        with self.assertRaises(TypeError):
            in0 = tree.interface.new_socket("Input 0", socket_type=socket_type, in_out='INPUT')
            self.assertIsNone(in0, f"Socket created for invalid type {socket_type}")
        with self.assertRaises(TypeError):
            out0 = tree.interface.new_socket("Output 0", socket_type=socket_type, in_out='OUTPUT')
            self.assertIsNone(out0, f"Socket created for invalid type {socket_type}")

    def do_test_sockets_in_out(self, socket_type):
        tree, group_node = self.make_group_and_instance()

        out0 = tree.interface.new_socket("Output 0", socket_type=socket_type, in_out='OUTPUT')
        self.assertIsNotNone(out0, f"Could not create socket of type {socket_type}")

        in0 = tree.interface.new_socket("Input 0", socket_type=socket_type, in_out='INPUT')
        self.assertIsNotNone(in0, f"Could not create socket of type {socket_type}")

        in1 = tree.interface.new_socket("Input 1", socket_type=socket_type, in_out='INPUT')
        self.assertIsNotNone(in1, f"Could not create socket of type {socket_type}")

        out1 = tree.interface.new_socket("Output 1", socket_type=socket_type, in_out='OUTPUT')
        self.assertIsNotNone(out1, f"Could not create socket of type {socket_type}")

        self.assertSequenceEqual([(s.name, s.bl_idname) for s in group_node.inputs], [
            ("Input 0", socket_type),
            ("Input 1", socket_type),
        ])
        self.assertSequenceEqual([(s.name, s.bl_idname) for s in group_node.outputs], [
            ("Output 0", socket_type),
            ("Output 1", socket_type),
        ])

    def do_test_user_count(self, value, expected_users):
        if (isinstance(value, bpy.types.ID)):
            self.assertEqual(
                value.users,
                expected_users,
                f"Socket default value has user count {value.users}, expected {expected_users}")

    def do_test_socket_type(self, socket_type, subtype=None, dimensions=None):
        default_value = self.make_default_socket_value(socket_type)
        compare_value = self.make_socket_value_comparator(socket_type)

        # Create the tree first, add sockets, then create a group instance.
        # That way the new instance should reflect the expected default values.
        tree = self.make_group()

        in0 = tree.interface.new_socket("Input 0", socket_type=socket_type, in_out='INPUT')
        if default_value is not None:
            in0.default_value = default_value
        out0 = tree.interface.new_socket("Output 0", socket_type=socket_type, in_out='OUTPUT')
        self.assertIsNotNone(in0, f"Could not create socket of type {socket_type}")
        self.assertIsNotNone(out0, f"Could not create socket of type {socket_type}")
        # Note: the type of the socket python object remains the same even when
        # the actual type of the socket in the tree changes due to changing the
        # subtype and/or dimensions! It would be nice if that can be avoided in
        # the future, but for now is expected behavior.
        in0_old_suffix = in0.bl_socket_idname.removeprefix("Node")
        out0_old_suffix = out0.bl_socket_idname.removeprefix("Node")
        expect_same_idname = True
        if subtype is not None:
            if subtype != in0.subtype:
                expect_same_idname = False
            in0.subtype = subtype
            out0.subtype = subtype
        if dimensions is not None:
            if dimensions != in0.dimensions:
                expect_same_idname = False
            in0.dimensions = dimensions
            out0.dimensions = dimensions

        self.assertEqual(type(in0).__name__.removeprefix("NodeTreeInterface"), in0_old_suffix)
        self.assertEqual(type(out0).__name__.removeprefix("NodeTreeInterface"), out0_old_suffix)
        # Get the sockets from the tree again to use the correct the type.
        in0 = tree.interface.items_tree[in0.identifier]
        out0 = tree.interface.items_tree[out0.identifier]
        if expect_same_idname:
            self.assertEqual(type(in0).__name__.removeprefix("NodeTreeInterface"), in0_old_suffix)
            self.assertEqual(type(out0).__name__.removeprefix("NodeTreeInterface"), out0_old_suffix)
        else:
            self.assertNotEqual(type(in0).__name__.removeprefix("NodeTreeInterface"), in0_old_suffix)
            self.assertNotEqual(type(out0).__name__.removeprefix("NodeTreeInterface"), out0_old_suffix)

        # Now make a node group instance to check default values.
        group_node = self.make_instance(tree)
        if compare_value:
            compare_value(self, group_node.inputs[0].default_value, in0.default_value)

        # Test ID user count after assigning.
        if (hasattr(in0, "default_value")):
            # The default value is stored in both the interface and node, it should have 2 users now.
            self.do_test_user_count(in0.default_value, 2)

        # Copy sockets
        in1 = tree.interface.copy(in0)
        out1 = tree.interface.copy(out0)
        self.assertIsNotNone(in1, "Could not copy socket")
        self.assertIsNotNone(out1, "Could not copy socket")
        # User count on default values should increment by 2 after copy,
        # one user for the interface and one for the group node instance.
        if (hasattr(in1, "default_value")):
            self.do_test_user_count(in1.default_value, 4)

        tree2 = self.make_group()
        inCrossTreeCopy = tree2.interface.copy(in0)
        outCrossTreeCopy = tree2.interface.copy(out1)
        self.assertIsNotNone(inCrossTreeCopy, "Could not copy socket to other tree")
        self.assertIsNotNone(outCrossTreeCopy, "Could not copy socket to other tree")

    # Classic outputs..inputs socket layout
    def do_test_items_order_classic(self, socket_type):
        tree, group_node = self.make_group_and_instance()

        tree.interface.new_socket("Output 0", socket_type=socket_type, in_out='OUTPUT')
        tree.interface.new_socket("Input 0", socket_type=socket_type, in_out='INPUT')

        self.assertSequenceEqual([(s.name, s.item_type) for s in tree.interface.items_tree], [
            ("Output 0", 'SOCKET'),
            ("Input 0", 'SOCKET'),
        ])
        self.assertSequenceEqual([s.name for s in group_node.inputs], [
            "Input 0",
        ])
        self.assertSequenceEqual([s.name for s in group_node.outputs], [
            "Output 0",
        ])
        # XXX currently no panel state access on node instances.
        # self.assertFalse(group_node.panels)

    # Mixed sockets and panels
    def do_test_items_order_mixed_with_panels(self, socket_type):
        tree, group_node = self.make_group_and_instance()

        tree.interface.new_panel("Panel 0")
        tree.interface.new_socket("Input 0", socket_type=socket_type, in_out='INPUT')
        tree.interface.new_socket("Output 0", socket_type=socket_type, in_out='OUTPUT')
        tree.interface.new_panel("Panel 1")
        tree.interface.new_socket("Input 1", socket_type=socket_type, in_out='INPUT')
        tree.interface.new_panel("Panel 2")
        tree.interface.new_socket("Output 1", socket_type=socket_type, in_out='OUTPUT')
        tree.interface.new_panel("Panel 3")

        # Panels after sockets
        self.assertSequenceEqual([(s.name, s.item_type) for s in tree.interface.items_tree], [
            ("Output 0", 'SOCKET'),
            ("Output 1", 'SOCKET'),
            ("Input 0", 'SOCKET'),
            ("Input 1", 'SOCKET'),
            ("Panel 0", 'PANEL'),
            ("Panel 1", 'PANEL'),
            ("Panel 2", 'PANEL'),
            ("Panel 3", 'PANEL'),
        ])
        self.assertSequenceEqual([s.name for s in group_node.inputs], [
            "Input 0",
            "Input 1",
        ])
        self.assertSequenceEqual([s.name for s in group_node.outputs], [
            "Output 0",
            "Output 1",
        ])
        # XXX currently no panel state access on node instances.
        # self.assertSequenceEqual([p.name for p in group_node.panels], [
        #     "Panel 0",
        #     "Panel 1",
        #     "Panel 2",
        #     "Panel 3",
        #     ])

    def do_test_add(self, socket_type):
        tree, group_node = self.make_group_and_instance()

        in0 = tree.interface.new_socket("Input 0", socket_type=socket_type, in_out='INPUT')
        self.assertSequenceEqual(tree.interface.items_tree, [in0])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 0"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], [])

        out0 = tree.interface.new_socket("Output 0", socket_type=socket_type, in_out='OUTPUT')
        self.assertSequenceEqual(tree.interface.items_tree, [out0, in0])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 0"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 0"])

        panel0 = tree.interface.new_panel("Panel 0")
        self.assertSequenceEqual(tree.interface.items_tree, [out0, in0, panel0])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 0"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 0"])

        # Add items to the panel.
        in1 = tree.interface.new_socket("Input 1", socket_type=socket_type, in_out='INPUT', parent=panel0)
        self.assertSequenceEqual(tree.interface.items_tree, [out0, in0, panel0, in1])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 0", "Input 1"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 0"])

        out1 = tree.interface.new_socket("Output 1", socket_type=socket_type, in_out='OUTPUT', parent=panel0)
        self.assertSequenceEqual(tree.interface.items_tree, [out0, in0, panel0, out1, in1])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 0", "Input 1"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 0", "Output 1"])

    def do_test_remove(self, socket_type):
        tree, group_node = self.make_group_and_instance()

        in0 = tree.interface.new_socket("Input 0", socket_type=socket_type, in_out='INPUT')
        out0 = tree.interface.new_socket("Output 0", socket_type=socket_type, in_out='OUTPUT')
        panel0 = tree.interface.new_panel("Panel 0")
        in1 = tree.interface.new_socket("Input 1", socket_type=socket_type, in_out='INPUT', parent=panel0)
        out1 = tree.interface.new_socket("Output 1", socket_type=socket_type, in_out='OUTPUT', parent=panel0)
        panel1 = tree.interface.new_panel("Panel 1")
        in2 = tree.interface.new_socket("Input 2", socket_type=socket_type, in_out='INPUT', parent=panel1)
        out2 = tree.interface.new_socket("Output 2", socket_type=socket_type, in_out='OUTPUT', parent=panel1)
        panel2 = tree.interface.new_panel("Panel 2")

        self.assertSequenceEqual(tree.interface.items_tree, [out0, in0, panel0, out1, in1, panel1, out2, in2, panel2])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 0", "Input 1", "Input 2"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 0", "Output 1", "Output 2"])

        # Remove from root panel.
        tree.interface.remove(in0)
        self.assertSequenceEqual(tree.interface.items_tree, [out0, panel0, out1, in1, panel1, out2, in2, panel2])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 1", "Input 2"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 0", "Output 1", "Output 2"])

        # Removing a panel should move content to the parent.
        tree.interface.remove(panel0)
        self.assertSequenceEqual(tree.interface.items_tree, [out0, out1, in1, panel1, out2, in2, panel2])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 1", "Input 2"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 0", "Output 1", "Output 2"])

        tree.interface.remove(out0)
        self.assertSequenceEqual(tree.interface.items_tree, [out1, in1, panel1, out2, in2, panel2])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 1", "Input 2"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 1", "Output 2"])

        # Remove content from panel
        tree.interface.remove(out2)
        self.assertSequenceEqual(tree.interface.items_tree, [out1, in1, panel1, in2, panel2])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 1", "Input 2"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 1"])

        # Remove a panel and its content
        tree.interface.remove(panel1, move_content_to_parent=False)
        self.assertSequenceEqual(tree.interface.items_tree, [out1, in1, panel2])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 1"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 1"])

        # Remove empty panel
        tree.interface.remove(panel2)
        self.assertSequenceEqual(tree.interface.items_tree, [out1, in1])
        self.assertSequenceEqual([s.name for s in group_node.inputs], ["Input 1"])
        self.assertSequenceEqual([s.name for s in group_node.outputs], ["Output 1"])

    def do_test_move(self, socket_type):
        tree, group_node = self.make_group_and_instance()

        in0 = tree.interface.new_socket("Input 0", socket_type=socket_type, in_out='INPUT')
        in1 = tree.interface.new_socket("Input 1", socket_type=socket_type, in_out='INPUT', parent=panel0)
        out0 = tree.interface.new_socket("Output 0", socket_type=socket_type, in_out='OUTPUT')
        out1 = tree.interface.new_socket("Output 1", socket_type=socket_type, in_out='OUTPUT', parent=panel0)
        panel0 = tree.interface.new_panel("Panel 0")
        panel1 = tree.interface.new_panel("Panel 1")


class NodeGroupInterfaceAnimationTest(AbstractNodeGroupInterfaceTest):
    socket_values = {"A": 11.0, "B": 22.0, "C": 33.0}

    def make_group_node(self, group_input=False):
        group = bpy.data.node_groups.new("Socket group", "GeometryNodeTree")
        for name, value in self.socket_values.items():
            socket = group.interface.new_socket(name, in_out='INPUT', socket_type='NodeSocketFloat')
            socket.default_value = value

        if group_input:
            node = group.nodes.new('NodeGroupInput')
            sockets = node.outputs
        else:
            tree = bpy.data.node_groups.new("Parent tree", "GeometryNodeTree")
            node = tree.nodes.new('GeometryNodeGroup')
            node.node_tree = group
            sockets = node.inputs
        for name, value in self.socket_values.items():
            sockets[name].default_value = value
        return group, node, sockets

    def make_driver_owner(self):
        obj = bpy.data.objects.new("Driver owner", None)
        bpy.context.scene.collection.objects.link(obj)
        return obj

    def add_socket_driver(self, owner, data_path, socket, index=-1):
        fcurve = owner.driver_add(data_path, index)
        fcurve.driver.expression = 'v'
        variable = fcurve.driver.variables.new()
        variable.name = 'v'
        variable.type = 'SINGLE_PROP'
        target = variable.targets[0]
        target.id_type = 'NODETREE'
        target.id = socket.id_data
        target.data_path = socket.path_from_id('default_value')
        target.use_fallback_value = True
        target.fallback_value = -10.0
        return fcurve

    def evaluated_location(self, obj):
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        return obj.evaluated_get(depsgraph).location.copy()

    def keyframe_sockets(self, sockets):
        for frame, multiplier in ((1, 1), (10, 2)):
            for name, value in self.socket_values.items():
                sockets[name].default_value = value * multiplier
                sockets[name].keyframe_insert('default_value', frame=frame)
        adt = sockets['A'].id_data.animation_data
        action, slot = adt.action, adt.action_slot
        return action, slot, action.layers[0].strips[0].channelbag(slot)

    def test_local_drivers_without_action(self):
        """Local driver destinations must follow sockets without an active Action."""
        for group_input in (False, True):
            with self.subTest(group_input=group_input):
                group, node, sockets = self.make_group_node(group_input)
                tree = node.id_data
                driver_a = sockets['A'].driver_add('default_value')
                driver_a.driver.expression = '11'
                driver_b = sockets['B'].driver_add('default_value')
                driver_b.driver.expression = '22'
                obj = self.make_driver_owner()
                self.add_socket_driver(obj, 'location', sockets['B'], index=0)
                self.assertIsNone(tree.animation_data.action)
                self.assertEqual(self.evaluated_location(obj).x, 22.0)

                driver_b.is_valid = False
                driver_b.driver.is_valid = False
                group.interface.move(group.interface.items_tree['B'], 0)
                self.assertEqual(driver_a.data_path, sockets['A'].path_from_id('default_value'))
                self.assertEqual(driver_b.data_path, sockets['B'].path_from_id('default_value'))
                self.assertTrue(driver_b.is_valid)
                self.assertTrue(driver_b.driver.is_valid)
                self.assertEqual(self.evaluated_location(obj).x, 22.0)

                # The removed driver also owns a target that needs remapping before it is freed.
                self.add_socket_driver(sockets['A'], 'default_value', sockets['C'])
                group.interface.remove(group.interface.items_tree['A'])
                self.assertEqual(len(tree.animation_data.drivers), 1)
                self.assertEqual(driver_b.data_path, sockets['B'].path_from_id('default_value'))
                self.assertEqual(self.evaluated_location(obj).x, 22.0)

    def test_external_driver_socket_reordering(self):
        """External targets must follow sockets even when the source tree has no AnimData."""
        for group_input in (False, True):
            with self.subTest(group_input=group_input):
                group, node, sockets = self.make_group_node(group_input)
                obj = self.make_driver_owner()
                drivers = {
                    name: self.add_socket_driver(obj, 'location', sockets[name], index=axis)
                    for axis, name in enumerate(self.socket_values)
                }
                self.assertIsNone(node.id_data.animation_data)
                self.assertEqual(tuple(self.evaluated_location(obj)), (11.0, 22.0, 33.0))
                drivers['B'].is_valid = False
                drivers['B'].driver.is_valid = False
                drivers['B'].mute = True
                drivers['C'].is_valid = False
                drivers['C'].driver.is_valid = False

                group.interface.move(group.interface.items_tree['B'], 0)
                for name, fcurve in drivers.items():
                    target = fcurve.driver.variables[0].targets[0]
                    self.assertEqual(target.data_path, sockets[name].path_from_id('default_value'))
                self.assertTrue(drivers['B'].is_valid)
                self.assertTrue(drivers['B'].driver.is_valid)
                self.assertTrue(drivers['B'].mute)
                self.assertFalse(drivers['C'].is_valid)
                self.assertFalse(drivers['C'].driver.is_valid)
                self.assertEqual(self.evaluated_location(obj).x, 11.0)
                drivers['B'].mute = False
                self.assertEqual(self.evaluated_location(obj).y, 22.0)

    def test_external_driver_socket_removal(self):
        """Deleting a referenced socket must evaluate the fallback immediately."""
        for group_input in (False, True):
            for removed_name in ('B', 'C'):
                with self.subTest(group_input=group_input, removed_socket=removed_name):
                    group, node, sockets = self.make_group_node(group_input)
                    survivor = 'C' if removed_name == 'B' else 'B'
                    obj = self.make_driver_owner()
                    removed_driver = self.add_socket_driver(obj, 'location', sockets[removed_name], index=0)
                    surviving_driver = self.add_socket_driver(obj, 'location', sockets[survivor], index=1)
                    self.assertIsNone(node.id_data.animation_data)
                    self.assertEqual(self.evaluated_location(obj).x, self.socket_values[removed_name])

                    group.interface.remove(group.interface.items_tree[removed_name])
                    removed_target = removed_driver.driver.variables[0].targets[0]
                    surviving_target = surviving_driver.driver.variables[0].targets[0]
                    self.assertEqual(removed_target.data_path, '')
                    self.assertEqual(removed_target.id, node.id_data)
                    self.assertEqual(len(obj.animation_data.drivers), 2)
                    self.assertEqual(surviving_target.data_path, sockets[survivor].path_from_id('default_value'))
                    value = self.evaluated_location(obj)
                    self.assertEqual(value.x, -10.0)
                    self.assertEqual(value.y, self.socket_values[survivor])

    def test_action_socket_remapping(self):
        """Active and NLA Actions must remap each used slot once, including muted strips."""
        for mode in ('active', 'nla', 'muted_nla', 'shared'):
            with self.subTest(mode=mode):
                group, node, sockets = self.make_group_node()
                tree = node.id_data
                action, slot, channelbag = self.keyframe_sockets(sockets)
                curves = {name: channelbag.fcurves.find(sockets[name].path_from_id('default_value'))
                          for name in self.socket_values}
                tracks = []
                if mode != 'active':
                    for _ in range(2 if mode == 'shared' else 1):
                        track = tree.animation_data.nla_tracks.new()
                        strip = track.strips.new("Socket animation", 1, action)
                        strip.action_slot = slot
                        track.mute = mode == 'muted_nla'
                        tracks.append(track)
                    if mode != 'shared':
                        tree.animation_data.action = None
                obj = self.make_driver_owner()
                self.add_socket_driver(obj, 'location', sockets['B'], index=0)

                group.interface.move(group.interface.items_tree['B'], 0)
                for name, fcurve in curves.items():
                    self.assertEqual(fcurve.data_path, sockets[name].path_from_id('default_value'))
                for track in tracks:
                    track.mute = False
                for frame, expected in ((1, 22.0), (10, 44.0)):
                    bpy.context.scene.frame_set(frame)
                    self.assertEqual(self.evaluated_location(obj).x, expected)

                # Removing the last socket isolates Action deletion from reordering updates.
                group.interface.remove(group.interface.items_tree['C'])
                self.assertEqual(len(channelbag.fcurves), 2)
                depsgraph = bpy.context.evaluated_depsgraph_get()
                evaluated_action = action.evaluated_get(depsgraph)
                evaluated_channelbag = evaluated_action.layers[0].strips[0].channelbag(slot)
                self.assertEqual(len(evaluated_channelbag.fcurves), 2)
                for frame, expected in ((1, 22.0), (10, 44.0)):
                    bpy.context.scene.frame_set(frame)
                    self.assertEqual(self.evaluated_location(obj).x, expected)

    def make_shared_action_nodes(self, output_sockets, mode):
        group = bpy.data.node_groups.new("Shared socket group", "GeometryNodeTree")
        direction = 'OUTPUT' if output_sockets else 'INPUT'
        for name, value in self.socket_values.items():
            socket = group.interface.new_socket(name, in_out=direction, socket_type='NodeSocketFloat')
            socket.default_value = value
        tree = bpy.data.node_groups.new("Shared Action tree", "GeometryNodeTree")
        for _ in range(2):
            node = tree.nodes.new('GeometryNodeGroup')
            node.node_tree = group
            sockets = node.outputs if output_sockets else node.inputs
            action, slot, channelbag = self.keyframe_sockets(sockets)

        other_tree = tree.copy()
        other_tree.animation_data.action = action
        other_tree.animation_data.action_slot = slot
        tracks = []
        if mode != 'active':
            for parent in (tree, other_tree):
                track = parent.animation_data.nla_tracks.new()
                strip = track.strips.new("Shared socket animation", 1, action)
                strip.action_slot = slot
                track.mute = mode == 'muted_nla'
                parent.animation_data.action = None
                tracks.append(track)

        observers = []
        for parent in (tree, other_tree):
            for node in parent.nodes:
                sockets = node.outputs if output_sockets else node.inputs
                obj = self.make_driver_owner()
                for axis, name in enumerate(self.socket_values):
                    self.add_socket_driver(obj, 'location', sockets[name], index=axis)
                observers.append(obj)
        return group, tree, channelbag, tracks, observers

    def test_shared_action_slot_socket_reordering(self):
        """Shared curves must move once, while other nodes and later edits still update."""
        for output_sockets in (False, True):
            for mode in ('active', 'nla', 'muted_nla'):
                with self.subTest(output_sockets=output_sockets, mode=mode):
                    group, tree, channelbag, tracks, observers = self.make_shared_action_nodes(output_sockets, mode)
                    for position in (0, 2):
                        group.interface.move(group.interface.items_tree['B'], position)
                        expected_paths = set()
                        for node in tree.nodes:
                            sockets = node.outputs if output_sockets else node.inputs
                            expected_paths.update(sockets[name].path_from_id('default_value')
                                                  for name in self.socket_values)
                        self.assertEqual({curve.data_path for curve in channelbag.fcurves}, expected_paths)
                        for track in tracks:
                            track.mute = False
                        for frame, multiplier in ((1, 1), (10, 2)):
                            bpy.context.scene.frame_set(frame)
                            for obj in observers:
                                self.assertEqual(tuple(self.evaluated_location(obj)),
                                                 tuple(value * multiplier for value in self.socket_values.values()))

    def test_shared_action_slot_socket_removal(self):
        """Deletion must preserve curves already moved by another tree in this update."""
        for output_sockets in (False, True):
            for mode in ('active', 'nla', 'muted_nla'):
                with self.subTest(output_sockets=output_sockets, mode=mode):
                    group, tree, channelbag, tracks, observers = self.make_shared_action_nodes(output_sockets, mode)
                    # C takes B's old index. Updating the second tree must not delete C's curves.
                    for removed_name, surviving_names in (('B', ('A', 'C')), ('C', ('A',))):
                        group.interface.remove(group.interface.items_tree[removed_name])
                        expected_paths = set()
                        for node in tree.nodes:
                            sockets = node.outputs if output_sockets else node.inputs
                            expected_paths.update(sockets[name].path_from_id('default_value')
                                                  for name in surviving_names)
                        self.assertEqual({curve.data_path for curve in channelbag.fcurves}, expected_paths)
                        for track in tracks:
                            track.mute = False
                        for frame, multiplier in ((1, 1), (10, 2)):
                            bpy.context.scene.frame_set(frame)
                            expected = tuple(value * multiplier if name in surviving_names else -10.0
                                             for name, value in self.socket_values.items())
                            for obj in observers:
                                self.assertEqual(tuple(self.evaluated_location(obj)), expected)

    def test_shared_action_other_slot_unchanged(self):
        """Remapping one tree must not change another slot with identical RNA paths."""
        group, node, sockets = self.make_group_node()
        action, slot, channelbag = self.keyframe_sockets(sockets)
        curve_b = channelbag.fcurves.find(sockets['B'].path_from_id('default_value'))
        _, other_node, other_sockets = self.make_group_node()
        other_tree = other_node.id_data
        other_path = other_sockets['B'].path_from_id('default_value')
        self.assertEqual(other_path, sockets['B'].path_from_id('default_value'))
        other_slot = action.slots.new('NODETREE', other_tree.name)
        other_channelbag = action.layers[0].strips[0].channelbags.new(other_slot)
        other_curve = other_channelbag.fcurves.new(other_path)
        other_curve.keyframe_points.insert(1, 202.0)
        other_curve.keyframe_points.insert(10, 303.0)
        other_tree.animation_data_create().action = action
        other_tree.animation_data.action_slot = other_slot
        obj = self.make_driver_owner()
        other_obj = self.make_driver_owner()
        self.add_socket_driver(obj, 'location', sockets['B'], index=0)
        self.add_socket_driver(other_obj, 'location', other_sockets['B'], index=0)

        group.interface.move(group.interface.items_tree['B'], 0)
        self.assertEqual(other_curve.data_path, other_path)
        self.assertEqual(curve_b.data_path, sockets['B'].path_from_id('default_value'))
        for frame, expected, other_expected in ((1, 22.0, 202.0), (10, 44.0, 303.0)):
            bpy.context.scene.frame_set(frame)
            self.assertEqual(self.evaluated_location(obj).x, expected)
            self.assertEqual(self.evaluated_location(other_obj).x, other_expected)


class GeometryNodeGroupInterfaceTest(AbstractNodeGroupInterfaceTest, NodeGroupInterfaceTests):
    tree_type = "GeometryNodeTree"
    group_node_type = "GeometryNodeGroup"

    def setUp(self):
        super().setUp()
        self.main_tree = bpy.data.node_groups.new("main", self.tree_type)

    def test_sockets_in_out(self):
        self.do_test_sockets_in_out("NodeSocketFloat")

    def test_all_socket_types(self):
        self.do_test_invalid_socket_type("INVALID_SOCKET_TYPE_11!1")
        self.do_test_socket_type("NodeSocketBool")
        self.do_test_socket_type("NodeSocketCollection")
        self.do_test_socket_type("NodeSocketColor")
        self.do_test_socket_type("NodeSocketFloat")
        self.do_test_socket_type("NodeSocketFloat", subtype='FACTOR')
        self.do_test_socket_type("NodeSocketGeometry")
        self.do_test_socket_type("NodeSocketImage")
        self.do_test_socket_type("NodeSocketInt")
        self.do_test_socket_type("NodeSocketInt", subtype='PERCENTAGE')
        self.do_test_socket_type("NodeSocketMaterial")
        self.do_test_socket_type("NodeSocketObject")
        self.do_test_socket_type("NodeSocketRotation")
        self.do_test_invalid_socket_type("NodeSocketShader")
        self.do_test_socket_type("NodeSocketString")
        self.do_test_invalid_socket_type("NodeSocketTexture")
        self.do_test_socket_type("NodeSocketVector")
        self.do_test_socket_type("NodeSocketVector", dimensions=2)
        self.do_test_socket_type("NodeSocketVector", dimensions=4)
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION')
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION', dimensions=2)
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION', dimensions=4)
        self.do_test_invalid_socket_type("NodeSocketVirtual")

    def test_items_order_classic(self):
        self.do_test_items_order_classic("NodeSocketFloat")

    def test_items_order_mixed_with_panels(self):
        self.do_test_items_order_mixed_with_panels("NodeSocketFloat")

    def test_add(self):
        self.do_test_add("NodeSocketFloat")

    def test_remove(self):
        self.do_test_remove("NodeSocketFloat")


class ShaderNodeGroupInterfaceTest(AbstractNodeGroupInterfaceTest, NodeGroupInterfaceTests):
    tree_type = "ShaderNodeTree"
    group_node_type = "ShaderNodeGroup"

    def setUp(self):
        super().setUp()
        self.material = bpy.data.materials.new("test")
        self.main_tree = self.material.node_tree

    def test_invalid_socket_type(self):
        self.do_test_invalid_socket_type("INVALID_SOCKET_TYPE_11!1")

    def test_sockets_in_out(self):
        self.do_test_sockets_in_out("NodeSocketFloat")

    def test_all_socket_types(self):
        self.do_test_socket_type("NodeSocketBool")
        self.do_test_invalid_socket_type("NodeSocketCollection")
        self.do_test_socket_type("NodeSocketColor")
        self.do_test_socket_type("NodeSocketFloat")
        self.do_test_socket_type("NodeSocketFloat", subtype='FACTOR')
        self.do_test_invalid_socket_type("NodeSocketGeometry")
        self.do_test_invalid_socket_type("NodeSocketImage")
        self.do_test_socket_type("NodeSocketInt")
        self.do_test_socket_type("NodeSocketInt", subtype='PERCENTAGE')
        self.do_test_invalid_socket_type("NodeSocketMaterial")
        self.do_test_invalid_socket_type("NodeSocketObject")
        self.do_test_invalid_socket_type("NodeSocketRotation")
        self.do_test_socket_type("NodeSocketShader")
        self.do_test_socket_type("NodeSocketString")
        self.do_test_invalid_socket_type("NodeSocketTexture")
        self.do_test_socket_type("NodeSocketVector")
        self.do_test_socket_type("NodeSocketVector", dimensions=2)
        self.do_test_socket_type("NodeSocketVector", dimensions=4)
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION')
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION', dimensions=2)
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION', dimensions=4)
        self.do_test_invalid_socket_type("NodeSocketVirtual")

    def test_items_order_classic(self):
        self.do_test_items_order_classic("NodeSocketFloat")

    def test_items_order_mixed_with_panels(self):
        self.do_test_items_order_mixed_with_panels("NodeSocketFloat")

    def test_add(self):
        self.do_test_add("NodeSocketFloat")

    def test_remove(self):
        self.do_test_remove("NodeSocketFloat")


class CompositorNodeGroupInterfaceTest(AbstractNodeGroupInterfaceTest, NodeGroupInterfaceTests):
    tree_type = "CompositorNodeTree"
    group_node_type = "CompositorNodeGroup"

    def setUp(self):
        super().setUp()
        self.scene = bpy.data.scenes.new("test")
        self.main_tree = bpy.data.node_groups.new("test node tree", "CompositorNodeTree")
        self.scene.compositing_node_group = self.main_tree

    def test_invalid_socket_type(self):
        self.do_test_invalid_socket_type("INVALID_SOCKET_TYPE_11!1")

    def test_sockets_in_out(self):
        self.do_test_sockets_in_out("NodeSocketFloat")

    def test_all_socket_types(self):
        self.do_test_socket_type("NodeSocketBool")
        self.do_test_invalid_socket_type("NodeSocketCollection")
        self.do_test_socket_type("NodeSocketColor")
        self.do_test_socket_type("NodeSocketFloat")
        self.do_test_socket_type("NodeSocketFloat", subtype='FACTOR')
        self.do_test_invalid_socket_type("NodeSocketGeometry")
        self.do_test_invalid_socket_type("NodeSocketImage")
        self.do_test_socket_type("NodeSocketInt")
        self.do_test_socket_type("NodeSocketInt", subtype='PERCENTAGE')
        self.do_test_invalid_socket_type("NodeSocketMaterial")
        self.do_test_socket_type("NodeSocketObject")
        self.do_test_socket_type("NodeSocketRotation")
        self.do_test_invalid_socket_type("NodeSocketShader")
        self.do_test_socket_type("NodeSocketString")
        self.do_test_invalid_socket_type("NodeSocketTexture")
        self.do_test_socket_type("NodeSocketVector")
        self.do_test_socket_type("NodeSocketVector", dimensions=2)
        self.do_test_socket_type("NodeSocketVector", dimensions=4)
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION')
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION', dimensions=2)
        self.do_test_socket_type("NodeSocketVector", subtype='TRANSLATION', dimensions=4)
        self.do_test_invalid_socket_type("NodeSocketVirtual")

    def test_items_order_classic(self):
        self.do_test_items_order_classic("NodeSocketFloat")

    def test_items_order_mixed_with_panels(self):
        self.do_test_items_order_mixed_with_panels("NodeSocketFloat")

    def test_add(self):
        self.do_test_add("NodeSocketFloat")

    def test_remove(self):
        self.do_test_remove("NodeSocketFloat")


class NodeTreeItemsIteratorTest(AbstractNodeGroupInterfaceTest, NodeGroupInterfaceTests):
    tree_type = "ShaderNodeTree"
    group_node_type = "ShaderNodeGroup"

    def setUp(self):
        super().setUp()
        self.material = bpy.data.materials.new("test")
        self.main_tree = self.material.node_tree

    # Regression test for changes while iterating over tree interface items (#143551).
    # The iterator should remain valid when changing properties of a tree item.
    def test_items_iterator(self):
        tree, group_node = self.make_group_and_instance()

        tree.interface.new_socket("Input 0", socket_type="NodeSocketFloat", in_out='INPUT')
        tree.interface.new_socket("Input 1", socket_type="NodeSocketBool", in_out='INPUT')
        # The cache vector has a fixed buffer for small sizes, add enough sockets to force reallocation.
        for i in range(20):
            tree.interface.new_socket(f"Input {2 + i}", socket_type="NodeSocketColor", in_out='INPUT')

        # Iterate over items and change properties. The loop iterator must remain valid.
        for item in tree.interface.items_tree:
            if item.socket_type == "NodeSocketFloat":
                item.default_value = 500.0
            elif item.socket_type == "NodeSocketColor":
                item.default_value = (1, 0, 0, 1)
            elif item.socket_type == "NodeSocketBool":
                item.default_value = True


def main():
    global args
    import argparse

    if '--' in sys.argv:
        argv = [sys.argv[0]] + sys.argv[sys.argv.index('--') + 1:]
    else:
        argv = sys.argv

    parser = argparse.ArgumentParser()
    parser.add_argument('--testdir', required=True, type=pathlib.Path)
    args, remaining = parser.parse_known_args(argv)

    unittest.main(argv=remaining)


if __name__ == "__main__":
    main()
