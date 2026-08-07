import unittest

from facial_transforms import (
    aggregate_transform_deltas,
    unity_euler_degrees_to_blender_quaternion,
    unity_position_to_blender,
    unity_quaternion_to_blender,
)


class AggregateTransformDeltasTests(unittest.TestCase):
    def test_sums_all_deltas_for_same_bone(self):
        trs_array = [
            {
                "_path": "DrivenA",
                "_position": {"x": 0.1, "y": 0.0, "z": -0.2},
                "_scale": {"x": 0.0, "y": 0.1, "z": 0.0},
                "_rotation": {"x": 3.0, "y": 0.0, "z": -2.0},
            },
            {
                "_path": "DrivenA",
                "_position": {"x": -0.1, "y": 0.2, "z": 0.0},
                "_scale": {"x": 0.2, "y": 0.0, "z": 0.0},
                "_rotation": {"x": 1.0, "y": 4.0, "z": 2.0},
            },
        ]

        result = aggregate_transform_deltas(trs_array)

        self.assertEqual(
            result["DrivenA"],
            {
                "position": (-0.0, 0.2, -0.2),
                "scale": (0.2, 0.1, 0.0),
                "rotation": (4.0, 4.0, 0.0),
            },
        )

    def test_mirror_swaps_side_and_mirrors_values_before_summing(self):
        trs_array = [
            {
                "_path": "Eye_L",
                "_position": {"x": 0.3, "y": 0.1, "z": 0.0},
                "_scale": {"x": 0.0, "y": 0.0, "z": 0.0},
                "_rotation": {"x": 1.0, "y": 2.0, "z": 3.0},
            }
        ]

        result = aggregate_transform_deltas(trs_array, mirror=True)

        self.assertEqual(
            result["Eye_R"],
            {
                "position": (-0.3, 0.1, 0.0),
                "scale": (0.0, 0.0, 0.0),
                "rotation": (1.0, -2.0, -3.0),
            },
        )


class UnityBlenderConversionTests(unittest.TestCase):
    def test_position_uses_fbx_handedness_conversion(self):
        self.assertEqual(
            unity_position_to_blender((0.25, -0.5, 0.75)),
            (-0.25, -0.5, 0.75),
        )

    def test_rotation_reflects_x_axis(self):
        self.assertEqual(
            unity_quaternion_to_blender((0.1, 0.2, 0.3, 0.9)),
            (0.1, -0.2, -0.3, 0.9),
        )

    def test_euler_rotation_matches_umaviewer_conversion(self):
        result = unity_euler_degrees_to_blender_quaternion((10.0, 20.0, 30.0))
        expected = (0.03813457, -0.18930785, -0.23929834, 0.95154852)
        for actual, reference in zip(result, expected):
            self.assertAlmostEqual(actual, reference, places=7)


if __name__ == "__main__":
    unittest.main()
