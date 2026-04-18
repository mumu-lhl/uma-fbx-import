# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from bpy.types import Object
from bpy.types import PoseBone
import json
import os
import re

import bpy
import math
from mathutils import Euler, Quaternion, Vector, Matrix


bl_info = {
    "name": "UMA Fbx Import",
    "author": "Mumulhl (沐沐13号)",
    "description": "",
    "blender": (3, 6, 0),
    "version": (0, 1, 4),
    "location": "View3D > UI > UMA Fbx Import",
    "warning": "",
    "category": "Generic",
}


# ─── Mouth Shape Key Name Mapping ─────────────────────────────────────────────
MOUTH_NAME_MAP = [
    "Base",
    "Normal",
    "CheekA_L",
    "CheekA_R",
    "WaraiA",
    "WaraiB",
    "WaraiC",
    "WaraiD",
    "WaraiE",
    "IkariA",
    "IkariB",
    "KanasiA",
    "DoyaA",
    "DereA",
    "OdorokiA",
    "OdorokiB",
    "JitoA",
    "KomariA",
    "KusyoA_L",
    "KusyoA_R",
    "KusyoB_L",
    "KusyoB_R",
    "UreiA",
    "TalkA_A_S",
    "TalkA_A_L",
    "TalkA_I_S",
    "TalkA_I_L",
    "TalkA_U_S",
    "TalkA_U_L",
    "TalkA_E_S",
    "TalkA_E_L",
    "TalkA_O_S",
    "TalkA_O_L",
    "TalkB_A_S",
    "TalkB_A_L",
    "TalkB_I_S",
    "TalkB_I_L",
    "TalkB_E_S",
    "TalkB_E_L",
    "RunA",
    "RunB",
    "DrivenA",
    "ToothHide",
    "TalkC_I",
    "TanA",
    "TanB",
    "TanC_L",
    "TanD_L",
    "TanC_R",
    "TanD_R",
    "Offset_U",
    "Offset_D",
    "Offset_L",
    "Offset_R",
    "Scale_U",
    "Scale_D",
    "LowAngle",
]

# ─── Eyebrow Shape Key Name Mapping ────────────────────────────────────────────
EYEBROW_NAME_MAP = [
    "Base",
    "WaraiA",
    "WaraiB",
    "WaraiC",
    "WaraiD",
    "IkariA",
    "KanasiA",
    "DoyaA",
    "DereA",
    "OdorokiA",
    "OdorokiB",
    "JitoA",
    "KomariA",
    "KusyoA",
    "UreiA",
    "RunA",
    "RunB",
    "SeriousA",
    "SeriousB",
    "ShiwaA",
    "ShiwaB",
    "Offset_U",
    "Offset_D",
    "Offset_L",
    "Offset_R",
]

# ─── Eye Shape Key Name Mapping ────────────────────────────────────────────────
EYE_NAME_MAP = [
    "Base",
    "HalfA",
    "CloseA",
    "HalfB",
    "HalfC",
    "WaraiA",
    "WaraiB",
    "WaraiC",
    "WaraiD",
    "IkariA",
    "KanasiA",
    "DereA",
    "OdorokiA",
    "OdorokiB",
    "OdorokiC",
    "JitoA",
    "KusyoA",
    "UreiA",
    "RunA",
    "DrivenA",
    "XRange",
    "YRange",
    "EyeHideA",
    "SeriousA",
    "PupilA",
    "PupilB",
    "PupilC",
    "EyelidHideA",
    "EyelidHideB",
]

# Utils Functions


def select_pose_bone(pose_bone: PoseBone):
    if bpy.app.version >= (5, 0, 0):
        pose_bone.select = True
    else:
        pose_bone.bone.select = True


# ─── Blender Panel ─────────────────────────────────────────────────────────────


class UMA_PT_panel(bpy.types.Panel):
    """UMA Fbx Import Panel in 3D Viewport sidebar"""

    bl_label = "UMA Fbx Import"
    bl_idname = "UMA_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UMA Fbx Import"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "uma_data_directory")
        layout.operator("uma.one_click_import")
        layout.operator("uma.fix_face_shapekeys")


# ─── Blender Operator ──────────────────────────────────────────────────────────


class UMA_OT_one_click_import(bpy.types.Operator):
    """One-click import of body, character and tail FBX files"""

    bl_idname = "uma.one_click_import"
    bl_label = "一键导入"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene.uma_data_directory != ""

    def execute(self, context):
        data_dir = context.scene.uma_data_directory

        if not os.path.exists(data_dir):
            self.report({"ERROR"}, "Data directory does not exist")
            return {"CANCELLED"}

        patterns = [r"^pfb_bdy.*\.fbx$", r"^pfb_chr.*\.fbx$", r"^pfb_tail.*\.fbx$"]
        fbx_files = []

        for pattern in patterns:
            for f in os.scandir(data_dir):
                if f.is_file() and re.match(pattern, f.name):
                    fbx_files.append(f.path)
                    break

        if not fbx_files:
            self.report({"ERROR"}, "No matching FBX files found")
            return {"CANCELLED"}

        if not hasattr(bpy.ops.import_scene, "fbx"):
            self.report(
                {"ERROR"},
                "FBX import operator not found. Please enable the FBX addon in preferences.",
            )
            return {"CANCELLED"}

        imported_armatures: list[Object] = []
        for filepath in fbx_files:
            bpy.ops.import_scene.fbx(filepath=filepath)

        for obj in bpy.data.objects:
            if obj.type == "ARMATURE":
                self.clear_armature_scale(obj)
                imported_armatures.append(obj)

        body_armature = None
        tail_armature = None
        head_armature = None

        for armature in imported_armatures:
            if armature.name.startswith("pfb_bdy"):
                body_armature = armature
            else:
                for bone in armature.pose.bones:
                    if bone.name.startswith("pfb_tail"):
                        tail_armature = armature
                    elif bone.name.startswith("pfb_chr"):
                        head_armature = armature

        if tail_armature and body_armature:
            self.process_tail_armature(tail_armature, body_armature)
        if head_armature and body_armature:
            self.process_head_armature(head_armature, body_armature)

        if body_armature:
            # 设置骨骼在视口中显示在网格前面（不被模型遮挡）
            body_armature.show_in_front = True

            bpy.context.view_layer.objects.active = body_armature
            body_armature.select_set(True)
            bpy.ops.uma.fix_face_shapekeys()
            self.apply_armature_rotation(body_armature)
            self.fix_shoulder_bones(body_armature)

        return {"FINISHED"}

    def fix_shoulder_bones(self, armature: Object):
        """将 Shoulder 骨骼的尾端对齐到 Arm 骨骼的头端"""
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = armature.data.edit_bones

        pairs = [("Shoulder_L", "Arm_L"), ("Shoulder_R", "Arm_R")]
        for shoulder_name, arm_name in pairs:
            shoulder = edit_bones.get(shoulder_name)
            arm = edit_bones.get(arm_name)
            if shoulder and arm:
                # 将肩膀骨骼的尾部移动到手臂骨骼的头部
                shoulder.tail = arm.head

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()

    def align_armature_location(
        self,
        source_armature: Object,
        target_armature: Object,
        target_bone_name: str,
        source_bone_name: str = None,
    ):
        """通用的坐标对齐方案：只对齐位置，并应用变换，避免-90度翻转"""
        target_bone = target_armature.pose.bones.get(target_bone_name)
        if not target_bone:
            self.report(
                {"WARNING"}, f"Target bone {target_bone_name} missing for alignment."
            )
            return

        target_pos = target_armature.matrix_world @ target_bone.head

        # 如果源骨架有指定的对齐骨骼就用它，否则用物体的原点
        if source_bone_name and source_armature.pose.bones.get(source_bone_name):
            source_bone = source_armature.pose.bones.get(source_bone_name)
            source_pos = source_armature.matrix_world @ source_bone.head
        else:
            source_pos = source_armature.matrix_world.translation

        # 平移源骨架
        source_armature.location += target_pos - source_pos
        bpy.context.view_layer.update()

        # 选中并应用位置变换
        bpy.ops.object.select_all(action="DESELECT")
        source_armature.select_set(True)
        # 关键：只对网格物体应用变换。
        # 空物体如果是骨骼子级，不应参与 transform_apply，否则会丢失相对骨骼的偏移。
        for child in source_armature.children_recursive:
            if child.type == "MESH":
                child.select_set(True)

        bpy.context.view_layer.objects.active = source_armature
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    def rename_bones_and_vertex_groups(
        self, armature: Object, bone_names: list[str], prefix: str
    ) -> dict[str, str]:
        """通用的重命名方法，保护子骨架骨骼不被覆盖导致拉扯"""
        renamed_bones: dict[str, str] = {}
        for bone_name in bone_names:
            if bone_name not in armature.data.bones:
                continue

            new_bone_name = f"{prefix}_{bone_name}"
            suffix = 1
            base_new_name = new_bone_name
            while new_bone_name in armature.data.bones:
                new_bone_name = f"{base_new_name}_{suffix}"
                suffix += 1

            armature.data.bones[bone_name].name = new_bone_name
            renamed_bones[bone_name] = new_bone_name

            for child in armature.children_recursive:
                if child.type == "MESH" and bone_name in child.vertex_groups:
                    child.vertex_groups[bone_name].name = new_bone_name

        return renamed_bones

    def link_bones_to_body(
        self,
        body_armature: Object,
        bone_map: dict[str, str],
        target_parent_name: str = None,
    ):
        """通用的父子级绑定方法，无论是头还是尾巴都能完美挂载"""
        bpy.ops.object.select_all(action="DESELECT")
        body_armature.select_set(True)
        bpy.context.view_layer.objects.active = body_armature
        bpy.ops.object.mode_set(mode="EDIT")

        edit_bones = body_armature.data.edit_bones

        for original_name, new_name in bone_map.items():
            child_bone = edit_bones.get(new_name)

            # 如果指定了父级名称（例如 "Hip"）就用，没指定就自动找同名的（例如 Chr_Head -> Head）
            parent_name = target_parent_name if target_parent_name else original_name
            parent_bone = edit_bones.get(parent_name)

            if child_bone and parent_bone:
                child_bone.parent = parent_bone
                child_bone.use_connect = False

        bpy.ops.object.mode_set(mode="OBJECT")

    def delete_pfb_chr_bones(self, head_armature: Object):
        """删除头部骨架上 pfb_chr 开头的无用骨骼"""
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = head_armature.data.edit_bones

        # 收集所有 pfb_chr 开头的骨骼
        bones_to_delete = [b.name for b in edit_bones if b.name.startswith("pfb_chr")]

        for bone_name in bones_to_delete:
            bone = edit_bones.get(bone_name)
            if bone:
                edit_bones.remove(bone)

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()

    def process_head_armature(self, head_armature: Object, body_armature: Object):
        """处理头部：删除无用骨骼 -> 平移 -> 重命名 -> 合并 -> 连接到脖子"""
        # 1. 删除 pfb_chr 开头的无用骨骼
        self.delete_pfb_chr_bones(head_armature)

        # 2. 对齐 Neck 骨骼到身体骨架的 Neck
        self.align_armature_location(
            head_armature,
            body_armature,
            target_bone_name="Neck",
            source_bone_name="Neck",
        )

        # 3. 重命名 Neck 和 Head 骨骼（保护性重命名）
        head_bone_map = self.rename_bones_and_vertex_groups(
            head_armature, ["Neck", "Head"], "Chr"
        )
        if not head_bone_map:
            return

        # 4. 合并骨架
        self.rebind_child_mesh_armature_modifiers(head_armature, body_armature)
        self.merge_armature_into_body(head_armature, body_armature)

        # 5. 绑定到身体的 Neck 上
        self.link_bones_to_body(body_armature, head_bone_map)

        # 6. 修复 Sp_ 骨骼朝向
        self.fix_sp_bone_orientations(body_armature)

    def delete_pfb_tail_bones(self, tail_armature: Object):
        """删除尾巴骨架上 pfb_tail 开头的无用骨骼"""
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = tail_armature.data.edit_bones

        # 收集所有 pfb_tail 开头的骨骼
        bones_to_delete = [b.name for b in edit_bones if b.name.startswith("pfb_tail")]

        for bone_name in bones_to_delete:
            bone = edit_bones.get(bone_name)
            if bone:
                edit_bones.remove(bone)

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()

    def scale_tail_ctrl_bone(self, tail_armature: Object, scale_factor: float = 2.0):
        """放大 Tail_Ctrl 骨骼，保持头端位置不动"""
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = tail_armature.data.edit_bones

        tail_ctrl_bone = edit_bones.get("Tail_Ctrl")
        if tail_ctrl_bone:
            # 计算从头到尾的方向
            direction = tail_ctrl_bone.tail - tail_ctrl_bone.head

            # 保持头端位置不变，将尾部按倍数放大
            tail_ctrl_bone.tail = tail_ctrl_bone.head + direction * scale_factor

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()

    def process_tail_armature(self, tail_armature: Object, body_armature: Object):
        """处理尾巴：删除无用骨骼 -> 放大 Tail_Ctrl -> 平移 -> 重命名 -> 合并 -> 连接到 Hip"""
        # 1. 删除 pfb_tail 开头的无用骨骼
        self.delete_pfb_tail_bones(tail_armature)

        # 2. 放大 Tail_Ctrl 骨骼（10倍）
        self.scale_tail_ctrl_bone(tail_armature, scale_factor=10.0)

        # 3. 尾巴骨架上的 Hip 骨骼像头部骨架上的 Head 那样处理
        # 检查尾巴是否有 Hip 骨骼
        if "Hip" not in tail_armature.data.bones:
            self.report({"WARNING"}, "Tail armature has no Hip bone.")
            return

        # 4. 对齐 Hip 骨骼到身体骨架的 Hip
        self.align_armature_location(
            tail_armature,
            body_armature,
            target_bone_name="Hip",
            source_bone_name="Hip",
        )

        # 5. 重命名 Hip 骨骼（保护性重命名）
        tail_bone_map = self.rename_bones_and_vertex_groups(
            tail_armature, ["Hip"], "Tail"
        )

        # 6. 合并骨架
        self.rebind_child_mesh_armature_modifiers(tail_armature, body_armature)
        self.merge_armature_into_body(tail_armature, body_armature)

        # 7. 绑定到身体的 Hip 上
        self.link_bones_to_body(body_armature, tail_bone_map, target_parent_name="Hip")

        # 8. 修复 Sp_ 骨骼朝向
        self.fix_sp_bone_orientations(body_armature)

    def rebind_child_mesh_armature_modifiers(
        self, source_armature: Object, target_armature: Object
    ):
        child_objects = list(source_armature.children_recursive)
        child_objects.extend(source_armature.children)

        for child in child_objects:
            if child.type != "MESH":
                continue

            for modifier in child.modifiers:
                if modifier.type == "ARMATURE" and modifier.object == source_armature:
                    modifier.object = target_armature

    def merge_armature_into_body(self, source_armature: Object, body_armature: Object):
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        body_armature.select_set(True)
        source_armature.select_set(True)
        bpy.context.view_layer.objects.active = body_armature
        bpy.ops.object.join()
        bpy.context.view_layer.update()

    def clear_armature_scale(self, armature: Object):
        armature.scale = Vector((1.0, 1.0, 1.0))
        bpy.context.view_layer.update()

    def apply_armature_rotation(self, armature: Object):
        """应用骨架对象的旋转，保留骨骼和网格的当前姿态"""
        bpy.ops.object.select_all(action="DESELECT")
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    def fix_sp_bone_orientations(self, armature: Object):
        """
        合并骨架后修复 Sp_ 骨骼链的朝向。

        Sp_ 骨骼形成链，末尾的两位数表示父子顺序。
        此函数：
        1. 按基础名称（不含后缀数字）将 Sp_ 骨骼分组为链
        2. 按后缀数字对每条链排序
        3. 调整骨骼朝向，使每根骨骼的尾部连接到下一根骨骼的头部
        4. 最后一根骨骼继承倒数第二根骨骼的朝向
        """
        bpy.ops.object.mode_set(mode="EDIT")

        # 收集所有 Sp_ 骨骼并按链分组
        edit_bones = armature.data.edit_bones
        sp_bone_chains = {}

        for bone in edit_bones:
            if bone.name.startswith("Sp_"):
                # 提取基础名称和后缀数字
                # 匹配模式：Sp_XXX_NN，其中 NN 是后缀数字（1-2位）
                # 例如：Sp_Th_Ribbon0_R_00, Sp_Th_Ribbon0_R_01, Sp_XXX_0, Sp_XXX_12
                match = re.match(r"^(Sp_.+?)_(\d{1,2})$", bone.name)
                if match:
                    base_name = match.group(1)
                    suffix = int(match.group(2))

                    if base_name not in sp_bone_chains:
                        sp_bone_chains[base_name] = []
                    sp_bone_chains[base_name].append((suffix, bone))

        # 处理每条链
        for base_name, chain in sp_bone_chains.items():
            # 按后缀数字排序
            chain.sort(key=lambda x: x[0])

            if len(chain) < 2:
                # 至少需要 2 根骨骼才能形成链
                continue

            # 处理链中的骨骼
            for i in range(len(chain)):
                suffix, bone = chain[i]

                if i < len(chain) - 1:
                    # 非最后一根骨骼：将尾部指向下一根骨骼的头部
                    next_suffix, next_bone = chain[i + 1]

                    # 计算从当前头部到下一根头部的方向
                    direction = next_bone.head - bone.head

                    # 设置骨骼尾部到下一根骨骼的头部位置
                    bone.tail = bone.head + direction
                else:
                    # 最后一根骨骼：继承倒数第二根骨骼的朝向
                    prev_suffix, prev_bone = chain[i - 1]

                    # 复制前一根骨骼的方向
                    prev_direction = prev_bone.tail - prev_bone.head

                    # 根据前一根骨骼的方向设置这根骨骼的尾部
                    bone.tail = bone.head + prev_direction

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()


# ─── Blender Operator ──────────────────────────────────────────────────────────


class UMA_OT_fix_face_shapekeys(bpy.types.Operator):
    """Fix Face Shapekeys by importing from facial target JSON"""

    bl_idname = "uma.fix_face_shapekeys"
    bl_label = "修复脸部形态键"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == "ARMATURE"
        )

    def find_mesh(self, armature, name):
        """Find mesh object by name that is a child of the armature or influenced by it"""
        for child in armature.children:
            if child.type == "MESH" and child.name == name:
                return child
        # Also check if any mesh object is parented to armature via armature modifier
        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj.name == name:
                # Check if this mesh is influenced by the armature
                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE" and modifier.object == armature:
                        return obj
        return None

    def capture_deformed_vertices_to_shapekey(self, face_mesh, shapekey_name):
        # Get the evaluated mesh (with armature modifier applied)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_obj = face_mesh.evaluated_get(depsgraph)
        mesh_temp = evaluated_obj.to_mesh()

        # Check if Basis shape key exists
        if (
            not face_mesh.data.shape_keys
            or "Basis" not in face_mesh.data.shape_keys.key_blocks
        ):
            self.report({"ERROR"}, "Basis shapekey not found")
            evaluated_obj.to_mesh_clear()
            return None

        # Create new shape key
        new_shapekey = face_mesh.shape_key_add(name=shapekey_name, from_mix=False)

        # Copy vertex positions from evaluated mesh to shape key
        shapekey_block = new_shapekey
        for i, vertex in enumerate(mesh_temp.vertices):
            if i < len(shapekey_block.data):
                shapekey_block.data[i].co = vertex.co

        # Clean up temporary mesh
        evaluated_obj.to_mesh_clear()

        return new_shapekey

    def create_basis_shapekey(self, mesh_obj):
        if not mesh_obj.data.shape_keys:
            # First shapekey automatically becomes Basis
            mesh_obj.shape_key_add(name="Basis")
            bpy.context.view_layer.update()
        elif "Basis" not in mesh_obj.data.shape_keys.key_blocks:
            self.report(
                {"WARNING"}, "No Basis shapekey found, creating one at current state"
            )
            mesh_obj.shape_key_add(name="Basis")
            bpy.context.view_layer.update()

    def store_bone_states(self, armature):
        """Store original bone states for restoration"""
        bone_states = {}
        for bone in armature.pose.bones:
            bone_states[bone.name] = {
                "location": bone.location.copy(),
                "rotation_mode": bone.rotation_mode,
                "rotation_euler": bone.rotation_euler.copy(),
                "rotation_quaternion": bone.rotation_quaternion.copy(),
                "scale": bone.scale.copy(),
            }
        return bone_states

    def restore_bone_states(self, armature, bone_states):
        """Restore bones to their original states"""
        for bone_name, state in bone_states.items():
            bone = armature.pose.bones[bone_name]
            bone.location = state["location"]
            bone.rotation_mode = state["rotation_mode"]
            bone.rotation_euler = state["rotation_euler"]
            bone.rotation_quaternion = state["rotation_quaternion"]
            bone.scale = state["scale"]
        bpy.context.view_layer.update()

    def rot_from_maya(self, euler_angle) -> Quaternion:
        rad_x = math.radians(euler_angle[0])
        rad_y = math.radians(euler_angle[1])
        rad_z = math.radians(euler_angle[2])

        eul = Euler((rad_x, rad_y, rad_z), "XYZ")

        return eul.to_quaternion()

    def transform_bone(
        self, obj, bone_name: str, position, scale, rotation, is_override: bool
    ):
        bone = obj.pose.bones[bone_name]

        if is_override:
            bone.location = Vector((position["x"], -position["z"], position["y"]))
            bone.scale = Vector((scale["x"], scale["y"], scale["z"]))

            bone.rotation_mode = "XYZ"
            bone.rotation_euler[0] = rotation["x"]
            bone.rotation_euler[1] = rotation["y"]
            bone.rotation_euler[2] = rotation["z"]
        else:
            bone.location += Vector((-position["x"], position["y"], position["z"]))
            bone.scale += Vector((scale["x"], scale["y"], scale["z"]))

            bone.rotation_quaternion = self.rot_from_maya(
                (rotation["x"], rotation["y"], rotation["z"])
            )

        bpy.context.view_layer.update()

    def execute(self, context):
        armature = context.active_object
        data_dir = context.scene.uma_data_directory

        if not data_dir:
            self.report({"ERROR"}, "Please select a data directory first")
            return {"CANCELLED"}

        pattern = r"^ast_chr\d{4}_\d{2}_facial_target\.json$"

        if not os.path.exists(data_dir):
            self.report({"ERROR"}, "Data directory does not exist")
            return {"CANCELLED"}

        filepath = next(
            (
                f.path
                for f in os.scandir(data_dir)
                if f.is_file() and re.match(pattern, f.name)
            ),
            None,
        )

        if filepath is None:
            self.report({"ERROR"}, "No facial target JSON file found")
            return {"CANCELLED"}

        # Find and join M_Mayu into M_Face before processing
        face_mesh = self.find_mesh(armature, "M_Face")
        mayu_mesh = self.find_mesh(armature, "M_Mayu")

        if face_mesh and mayu_mesh:
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            mayu_mesh.select_set(True)
            face_mesh.select_set(True)
            bpy.context.view_layer.objects.active = face_mesh
            bpy.ops.object.join()
            bpy.context.view_layer.update()

        if not face_mesh:
            self.report({"ERROR"}, "M_Face mesh not found as child of armature")
            return {"CANCELLED"}

        # IMPORTANT: Store original bone states FIRST (before any transformations)
        original_bone_states = self.store_bone_states(armature)

        # Switch to OBJECT mode for shapekey operations
        bpy.ops.object.mode_set(mode="OBJECT")

        # Create Basis shapekey NOW (bones are still in rest state)
        self.create_basis_shapekey(face_mesh)

        # Load JSON data
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        targets = ["_eyeTarget", "_eyebrowTarget", "_mouthTarget"]
        expression_index = 0

        # Process each expression
        for target in targets:
            target_data = data[target]

            index = 0
            for morph in target_data:
                if index == 0:
                    index = 1
                    continue

                # Apply all bone transformations for this expression
                face_group_infos = morph["_faceGroupInfo"]

                for i, face_group_info in enumerate(face_group_infos):
                    trs_array = face_group_info["_trsArray"]

                    # Determine names and mirror needs
                    tasks = []
                    if (
                        target == "_eyeTarget"
                        and index < len(EYE_NAME_MAP)
                        and EYE_NAME_MAP[index] in ["XRange", "YRange"]
                    ):
                        if EYE_NAME_MAP[index] == "XRange":
                            # i=1 is Left (XRange_L -> Inward -> Right)
                            # i=0 is Right (XRange_R -> Outward -> Right)
                            primary = "Eye_L(R)" if i == 1 else "Eye_R(R)"
                            mirrored = "Eye_R(L)" if i == 1 else "Eye_L(L)"
                        else:  # YRange
                            # i=1 is Left (YRange_L -> Up)
                            # i=0 is Right (YRange_R -> Down)
                            primary = "Eye_L(U)" if i == 1 else "Eye_R(D)"
                            mirrored = "Eye_R(U)" if i == 1 else "Eye_L(D)"
                        tasks.append((primary, False))
                        tasks.append((mirrored, True))
                    else:
                        if target == "_mouthTarget":
                            name = f"{MOUTH_NAME_MAP[index]}[Mouth]"
                        elif target == "_eyeTarget":
                            suffix = "L" if i == 1 else "R"
                            name = f"{EYE_NAME_MAP[index]}_{suffix}[Eye]"
                        elif target == "_eyebrowTarget":
                            suffix = "L" if i == 1 else "R"
                            name = f"{EYEBROW_NAME_MAP[index]}_{suffix}[Eyebrow]"
                        tasks.append((name, False))

                    for sk_name, mirror_mode in tasks:
                        new_shapekey = self.apply_and_capture(
                            armature,
                            face_mesh,
                            trs_array,
                            sk_name,
                            original_bone_states,
                            mirror=mirror_mode,
                        )

                        if new_shapekey is None:
                            self.report(
                                {"ERROR"}, f"Failed to create shapekey: {sk_name}"
                            )
                            return {"CANCELLED"}

                index += 1
                expression_index += 1

        # Final restoration - ensure bones are back to rest state
        self.restore_bone_states(armature, original_bone_states)
        bpy.context.view_layer.update()

        # Rotate Eye Bones Rest Pose
        self.rotate_eye_bones_rest(armature)

        # Fix Eye Bone Weights
        self.fix_eye_weights(armature, face_mesh)
        # Setup Eye Drivers
        self.setup_eye_drivers(armature, face_mesh)

        self.report(
            {"INFO"},
            f"Fixed {expression_index} shapekeys for armature: {armature.name}",
        )
        return {"FINISHED"}

    def rotate_eye_bones_rest(self, armature):
        """将眼睛骨骼在静置姿态下绕头端旋转 90 度"""
        # 确保骨架是活动物体
        bpy.context.view_layer.objects.active = armature
        # 切换到编辑模式
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = armature.data.edit_bones

        for name in ["Eye_L", "Eye_R"]:
            bone = edit_bones.get(name)
            if bone:
                # 以头端为原点绕 X 轴旋转 90 度
                rot_mat = Matrix.Rotation(math.radians(90), 3, "X")
                direction = bone.tail - bone.head
                bone.tail = bone.head + rot_mat @ direction

        # 回到物体模式
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()

    def setup_eye_drivers(self, armature, face_mesh):
        """为眼睛形态键添加驱动器，实现骨骼旋转驱动"""
        if not face_mesh.data.shape_keys:
            return

        kb_data = face_mesh.data.shape_keys.key_blocks

        # 驱动器配置：(形态键名称, 关联骨骼, 监听轴向, 方向系数)
        # 根据报告：Z轴旋转控制左右，X轴旋转控制上下
        drivers_config = [
            ("Eye_L(L)", "Eye_L", "ROT_Z", -1),
            ("Eye_L(R)", "Eye_L", "ROT_Z", 1),
            ("Eye_L(U)", "Eye_L", "ROT_X", -1),
            ("Eye_L(D)", "Eye_L", "ROT_X", 1),
            ("Eye_R(L)", "Eye_R", "ROT_Z", -1),
            ("Eye_R(R)", "Eye_R", "ROT_Z", 1),
            ("Eye_R(U)", "Eye_R", "ROT_X", -1),
            ("Eye_R(D)", "Eye_R", "ROT_X", 1),
        ]

        for sk_name, bone_name, axis, direction in drivers_config:
            if sk_name in kb_data and bone_name in armature.pose.bones:
                kb = kb_data[sk_name]
                # 清除旧驱动器
                kb.driver_remove("value")

                # 添加新驱动器
                drv_spec = kb.driver_add("value")
                drv = drv_spec.driver
                drv.type = "SCRIPTED"

                var = drv.variables.new()
                var.name = "rot"
                var.type = "TRANSFORMS"
                target = var.targets[0]
                target.id = armature
                target.bone_target = bone_name
                target.transform_type = axis
                target.transform_space = "LOCAL_SPACE"

                # 驱动器表达式：旋转弧度 * 方向系数 * 敏感度缩放(1.5)
                drv.expression = f"{var.name} * {direction} * 1.5"

    def apply_and_capture(
        self,
        armature,
        face_mesh,
        trs_array,
        shapekey_name,
        original_bone_states,
        mirror=False,
    ):
        """Helper to apply bone transforms (with optional mirroring) and capture a shape key"""
        # 1. Apply transformations
        for trs in trs_array:
            bone_name = trs["_path"]
            position = trs["_position"].copy()
            scale = trs["_scale"].copy()
            rotation = trs["_rotation"].copy()
            is_override = trs["IsOverrideTarget"] == 1

            if mirror:
                # Mirror bone name suffix
                if bone_name.endswith("_L"):
                    bone_name = bone_name[:-2] + "_R"
                elif bone_name.endswith("_R"):
                    bone_name = bone_name[:-2] + "_L"

                # Mirror position X (assuming X is left/right)
                position["x"] = -position["x"]
                # Mirror rotation Y and Z (assuming mirroring across YZ plane in Maya/UMA space)
                rotation["y"] = -rotation["y"]
                rotation["z"] = -rotation["z"]

            if bone_name not in armature.pose.bones:
                continue

            self.transform_bone(
                armature,
                bone_name,
                position,
                scale,
                rotation,
                is_override,
            )

        # Update viewport to apply deformations to mesh
        bpy.context.view_layer.update()

        # 2. Capture shapekey
        new_shapekey = self.capture_deformed_vertices_to_shapekey(
            face_mesh, shapekey_name
        )

        if new_shapekey:
            new_shapekey.value = 0.0

        # 3. Restore bones to rest state
        self.restore_bone_states(armature, original_bone_states)
        bpy.context.view_layer.update()

        return new_shapekey


    def fix_eye_weights(self, armature, face_mesh):
        """实现眼睛骨骼修复：将眼睛骨骼权重合并到头部"""
        # 确保处于物体模式且面部网格处于活动状态
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.objects.active = face_mesh

        # 权重混合（Weight Mixing）
        # 将眼睛骨骼的权重合并到头部骨骼，使眼睛物理固定
        eye_bones = ["Eye_L", "Eye_R"]
        head_bone = "Chr_Head" if "Chr_Head" in armature.data.bones else "Head"

        if head_bone in armature.data.bones:
            # 确保头部顶点组存在
            if head_bone not in face_mesh.vertex_groups:
                face_mesh.vertex_groups.new(name=head_bone)

            for eye_bone in eye_bones:
                if eye_bone in face_mesh.vertex_groups:
                    # 使用修改器混合权重
                    mod = face_mesh.modifiers.new(
                        name=f"TMP_MIX_{eye_bone}", type="VERTEX_WEIGHT_MIX"
                    )
                    mod.vertex_group_a = head_bone
                    mod.vertex_group_b = eye_bone
                    mod.mix_mode = "ADD"
                    mod.mix_set = "ALL"

                    # 应用修改器
                    bpy.ops.object.modifier_apply(modifier=mod.name)

                    # 删除原始眼睛顶点组
                    vg = face_mesh.vertex_groups.get(eye_bone)
                    if vg:
                        face_mesh.vertex_groups.remove(vg)


def register():
    bpy.utils.register_class(UMA_PT_panel)
    bpy.utils.register_class(UMA_OT_one_click_import)
    bpy.utils.register_class(UMA_OT_fix_face_shapekeys)
    bpy.types.Scene.uma_data_directory = bpy.props.StringProperty(
        name="数据目录", description="Select the data directory", subtype="DIR_PATH"
    )


def unregister():
    del bpy.types.Scene.uma_data_directory
    bpy.utils.unregister_class(UMA_OT_fix_face_shapekeys)
    bpy.utils.unregister_class(UMA_OT_one_click_import)
    bpy.utils.unregister_class(UMA_PT_panel)
