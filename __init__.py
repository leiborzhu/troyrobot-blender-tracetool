bl_info = {
    "name": "track_tool",
    "author": "zhuhe",
    "version": (0, 5, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Tools > Trace manage",
    "description": "轨迹管理工具",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}
import bpy
import os
import sys
import json

from bpy.props import (
        IntProperty,
        FloatProperty,
        StringProperty,
        BoolProperty,
        PointerProperty,
        EnumProperty
        )
def track_input(input_path):
    filepath = input_path
    files_name = input_path.split('\\')[-1]
    directory = files_name.strip(files_name)

    bpy.ops.wm.obj_import(filepath=filepath, directory=directory)

    # bpy.ops.wm.obj_import(filepath="input_path")



class Track_input(bpy.types.Operator):
    # output bvh
    bl_label='导入轨迹'
    bl_idname = 'obj.trackinput' # no da xie
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        traph = context.scene.traph
        track_input(traph.input_path)
        return {'FINISHED'}


class Track_ui(bpy.types.Panel):
    bl_idname = "Track_ui"
    bl_label = "轨迹管理工具"

    # 标签分类
    bl_category = "Tool"

    # ui_type
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # bl_context = ["objectmode", 'posemode']

    def draw(self, context):
        layout = self.layout
        layout.label(text="轨迹文件路径", icon="ARMATURE_DATA")

        col = layout.column()
        scene = context.scene.traph
        
        col.prop(scene, 'input_path', text="导入文件路径")
        col.operator("obj.trackinput", text="导入",icon="IMPORT")




# RNA属性
class track_property(bpy.types.PropertyGroup):
    
    input_path: bpy.props.StringProperty(name='input_path',subtype='FILE_PATH')

    

classGroup = [track_property,
              Track_ui,
              Track_input
]


def register():
    for item in classGroup:
        # print(1)
        bpy.utils.register_class(item)
    bpy.types.Scene.traph = bpy.props.PointerProperty(type=track_property)


def unregister():
    for item in classGroup:
        bpy.utils.unregister_class(item)


if __name__ == '__main__':
    register()
