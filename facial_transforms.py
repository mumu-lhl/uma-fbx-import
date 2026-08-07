"""Pure facial-target transform helpers."""

import math


def unity_position_to_blender(position):
    """Convert an Uma FBX local position from Unity to Blender coordinates."""
    x, y, z = position
    return (-x, y, z)


def unity_quaternion_to_blender(quaternion_xyzw):
    """Convert a Unity local quaternion across the FBX handedness change.

    Uma's FBX import reflects the X axis.  Rotations are axial vectors, so
    conjugating by that reflection keeps X and negates Y/Z.
    """
    x, y, z, w = quaternion_xyzw
    return (x, -y, -z, w)


def unity_euler_degrees_to_blender_quaternion(euler_degrees):
    """Convert UmaViewer's XYZ Euler degrees to Blender xyzw quaternion data."""
    x, y, z = (math.radians(value) for value in euler_degrees)
    c = math.cos(x / 2.0)
    d = math.cos(y / 2.0)
    e = math.cos(z / 2.0)
    f = math.sin(x / 2.0)
    g = math.sin(y / 2.0)
    h = math.sin(z / 2.0)

    unity_quaternion = (
        f * d * e - c * g * h,
        c * g * e + f * d * h,
        c * d * h - f * g * e,
        c * d * e + f * g * h,
    )
    return unity_quaternion_to_blender(unity_quaternion)


def aggregate_transform_deltas(trs_array, mirror=False):
    """Sum additive facial-target TRS deltas grouped by bone path."""
    result = {}

    for trs in trs_array:
        bone_name = trs["_path"]
        position = [trs["_position"][axis] for axis in ("x", "y", "z")]
        scale = [trs["_scale"][axis] for axis in ("x", "y", "z")]
        rotation = [trs["_rotation"][axis] for axis in ("x", "y", "z")]

        if mirror:
            if bone_name.endswith("_L"):
                bone_name = bone_name[:-2] + "_R"
            elif bone_name.endswith("_R"):
                bone_name = bone_name[:-2] + "_L"

            position[0] = -position[0]
            rotation[1] = -rotation[1]
            rotation[2] = -rotation[2]

        delta = result.setdefault(
            bone_name,
            {
                "position": [0.0, 0.0, 0.0],
                "scale": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
            },
        )
        for key, values in (("position", position), ("scale", scale), ("rotation", rotation)):
            for index, value in enumerate(values):
                delta[key][index] += value

    return {
        bone_name: {
            key: tuple(values) for key, values in delta.items()
        }
        for bone_name, delta in result.items()
    }
