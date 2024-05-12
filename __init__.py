bl_info = {
    "name": "trace_tool",
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
    
class PT_view3d_IK(bpy.types.Panel):
    bl_idname = "PT_view3d_IK"
    bl_label = "bvh文件ik工具"

    # 标签分类
    bl_category = "Tool"

    # ui_type
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # bl_context = ["objectmode", 'posemode']

    def draw(self, context):
        layout = self.layout
        layout.label(text="bvh导入", icon="ARMATURE_DATA")

        col = layout.column()
        scene = context.scene.uiProperty
        
        # 生成按钮
        col.prop(scene, 'input_path', text="导入文件路径")




# RNA属性
class uiProperty(bpy.types.PropertyGroup):
    
    input_path: bpy.props.StringProperty(name='input_path',subtype='FILE_PATH')

    

classGroup = [uiProperty,
              
              PT_view3d_IK
]


def register():
    for item in classGroup:
        # print(1)
        bpy.utils.register_class(item)
    bpy.types.Scene.uiProperty = bpy.props.PointerProperty(type=uiProperty)


def unregister():
    for item in classGroup:
        bpy.utils.unregister_class(item)


if __name__ == '__main__':
    register()
