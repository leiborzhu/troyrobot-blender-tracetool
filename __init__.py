bl_info = {
    "name": "track_tool",
    "author": "zhuhe",
    "version": (0, 8, 6),
    "blender": (3, 6, 8),
    "location": "View3D > Sidebar >Trace manage",
    "description": "轨迹管理工具",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}
# 0.9.0更新
# 喷涂可视化

import bpy
import os
import sys
import json
import math
import numpy as np

from bpy.props import (
        IntProperty,
        FloatProperty,
        StringProperty,
        BoolProperty,
        PointerProperty,
        EnumProperty
        )

# ------------导入轨迹类&obj转换&运行函数-----------

def json2obj(list_data, tmp_path:str, name:str):
    # --将协议list信息转为obj信息--
    # 轨迹协议格式如下：
    '''
    {   "p": [-1200, -1200, 1000],
        "n": [1, 0, 0],
        "speed": 50,
        "index": 0,
        "spray": true
        }
    '''
    num = len(list_data)
    if num < 2:
        raise ValueError("轨迹点数量必须大于等于2")
    print(name)
    name = name.split('.')[0]
    # 点坐标信息
    point_data = [[0.0, 0.0, 0.0] for _ in range(num)]
    # 法线坐标信息
    normal_data = [[0.0, 0.0, 0.0] for _ in range(num)]

    # index reshape
    index_offset = 0
    index_list = []
    for point in list_data:
        index_list.append(point['index'])
    index_offset = min(index_list)

    for point in list_data:
        index = point['index'] - index_offset
        print(index)
        print(point['p'])
        for p in range(3):
            point_data[index][p] = point['p'][p]
            normal_data[index][p] = point['n'][p]

    # obj文本信息，按照blender的obj格式写入点和白边信息
    point_lines = []
    normal_lines = []
    line_lines = []

    for point in point_data:
        point_lines.append(f"v {point[0]} {point[1]} {point[2]}\n")
    # for normal in normal_data:
        # normal_lines.append(f"vn {normal[0]} {normal[1]} {normal[2]}\n")

    for i in range(num - 1):
        line_lines.append(f"l {i+1} {i+2}\n")
    # line_lines.append(f"l {num} 1\n") # 当前默认轨迹不首尾相连

    # 写入obj文件
    all_lines = point_lines + normal_lines + line_lines
    with open(os.path.join(tmp_path, name + '.obj'), 'w') as f:
        f.writelines(all_lines)
        print(f"{name}.obj 写入完成")

def init_trans(obj):
        # 修复旋转、位置
        obj.rotation_euler[0] = 0
        obj.rotation_euler[1] = 0
        obj.rotation_euler[2] = 0

        obj.location[0] = 0
        obj.location[1] = 0
        obj.location[2] = 0

def track_input(input_path, tmp_path, traph):

    # 不被清除的保护列表
    protect_list = ['model']
    # 单位强制设置为毫米
    bpy.context.scene.unit_settings.length_unit = 'MILLIMETERS'

    filepath = input_path
    if sys.platform == 'darwin':
        file_name = filepath.split('/')[-1]
    else:
        file_name = input_path.split('\\')[-1]
    directory = file_name.strip(file_name)
    if not file_name.endswith('.json'):
        raise ValueError("请输入正确的json文件路径")
    if not directory.startswith(os.path.abspath(__file__)):
        directory = os.path.join(os.path.abspath(__file__), directory)

    if not os.path.exists(tmp_path):
        # 为支持mac设备如此设置
        # raise ValueError("请输入正确的临时文件放置路径")
        os.makedirs(tmp_path)
    
    if traph.clear_blend:
        for obj in bpy.data.objects:
            if obj.name not in protect_list:
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in bpy.data.meshes:
            if mesh.name not in protect_list:
                bpy.data.meshes.remove(mesh, do_unlink=True)
        for material in bpy.data.materials:
            bpy.data.materials.remove(material, do_unlink=True)

    # bpy.ops.wm.obj_import(filepath=filepath, directory=directory)
        
    # 读取json文件
    with open(filepath, 'r') as f:
        raw_data = json.load(f)
    # 目前轨迹的名称、数量不一定，如有可能无edge值，需通用化处理
    labels = []
    raw_name = file_name.split('.')[0] # raw_name like black_right_door....
    traph.track_name = raw_name
    tmp_data = {} 

    for key in raw_data.keys():
        labels.append(key)

    for lable in labels:
        
        label_name = lable.split('_')[-1] # traj_surface -> surface
        traj_data = raw_data[f'traj_{label_name}']

        json2obj(traj_data, tmp_path, f'{raw_name}_{label_name}')

        # 导入obj文件
        bpy.ops.wm.obj_import(filepath=os.path.join(tmp_path, f'{raw_name}_{label_name}.obj'), directory=tmp_path, global_scale=0.001)
        init_trans(bpy.context.object)
    

        # bpy.ops.wm.obj_import(filepath="input_path")
        # 处理speed, spary等其他信息
        # TODO: 目前没有blender合适自定义property承载这些信息，先利用tmp.json文件的形式处理

        tmp_traj_data = []

        for point in traj_data:
            tmp_traj_data.append({'speed': point['speed'], 'spray': point['spray'], 'index': point['index'], 'n': point['n']})

        tmp_data[f'traj_{label_name}'] = tmp_traj_data

       

        # 将轨迹本身设为不可选， 避免操作点时误选
        bpy.data.objects[f'{traph.track_name}_{label_name}'].hide_select = True

    with open(os.path.join(tmp_path, 'tmp.json'), 'w') as f:
        json.dump(tmp_data, f)
        print("临时数据写入完成")
    # 添加轴空物体
    normal_sim(tmp_path, traph)   


class Track_input(bpy.types.Operator):
    # output bvh
    bl_label='导入轨迹'
    bl_idname = 'obj.trackinput' # no da xie
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        traph = context.scene.traph
        track_input(traph.input_path, traph.tmp_path, traph)
        return {'FINISHED'}


# ------------导出轨迹类&运行函数-----------
def point_list_write(traph, label, tmp_data):
    scale = 1000 # 单位强制设置为毫米，此处scale为1000
    point_list = []
    pos_list = []
    nor_list = []
    num = len(bpy.data.meshes[traph.track_name + '_' + label].vertices) # example_name
    
    for i in range(num):
        obj = bpy.data.objects[traph.track_name + '_' + label + '_' + str(i)] # example_name_0

        pos_list.append(obj.location)
        # 弧度制 默认XYZ
        # todo 欧拉旋转数据转换为法线
        nor_out = euler_to_normal([obj.rotation_euler[0], obj.rotation_euler[1], obj.rotation_euler[2]])
        nor_list.append(nor_out)



    point_list = []
    for i in range(len(pos_list)):
        point_list.append({
            'p': [x*scale for x in pos_list[i]],
            'n': nor_list[i],
            'speed': tmp_data[i]['speed'],
            'spray': tmp_data[i]['spray'],
            'index': tmp_data[i]['index']
        })
    
    return point_list

# -----------法线表示类&运行函数-----------
def build_normal_obj(traph, pos, nor, index, track_name):
    scale = 0.06 # 箭头缩放信息待暴露
    # 为指定位置与方向设置法线
    bpy.ops.object.empty_add(type='SINGLE_ARROW', align='WORLD', location=(pos[0]/1000, pos[1]/1000, pos[2]/1000), scale=(scale, scale, scale))
    obj_tmp = bpy.context.object
    obj_tmp.name = track_name + '_' + str(index)
    obj_tmp.scale[0] = scale*3
    obj_tmp.scale[1] = scale*3
    obj_tmp.scale[2] = scale
    # 弧度制
    obj_tmp.rotation_euler[0] = nor[0]
    obj_tmp.rotation_euler[1] = nor[1]
    obj_tmp.rotation_euler[2] = nor[2]
    # 增加法线末端点
    bpy.ops.object.empty_add(type='SINGLE_ARROW', align='WORLD', location=(pos[0]/1000 + nor[0]*0.01, pos[1]/1000 + nor[1]*0.01, pos[2]/1000 + nor[2]*0.01), scale=(scale, scale, scale))
    nor_tmp = bpy.context.object
    nor_tmp.name = track_name + '_' + str(index) + '_norend'
    nor_tmp.scale[0] = scale*3
    nor_tmp.scale[1] = scale*3
    nor_tmp.scale[2] = scale

    # 增加约束器
    cons_rotation = obj_tmp.constraints.new('TRACK_TO')
    cons_rotation.name = 'normal'
    cons_rotation.target = bpy.data.objects[track_name + '_' + str(index) + '_norend']
    cons_rotation.track_axis = 'TRACK_Z'
    cons_rotation.up_axis = 'UP_Y'
    cons_rotation.target_space = 'WORLD'
    cons_rotation.owner_space = 'WORLD'

    # 删除临时对象
    bpy.context.view_layer.objects.active = obj_tmp
    # bpy.context.space_data.context = 'CONSTRAINT'
    bpy.ops.constraint.apply(constraint='normal')
    nor_tmp.hide_viewport = True
    bpy.data.objects.remove(bpy.data.objects[track_name + '_' + str(index) + '_norend'])

    """
    # 添加驱动器() # 该方案暂时搁置
    dri_pos_x = obj_tmp.driver_add('location', 0).driver
    dri_pos_y = obj_tmp.driver_add('location', 1).driver
    dri_pos_z = obj_tmp.driver_add('location', 2).driver

    def dri_config_location(con_driver: bpy.types.Driver, con_dict: dict):
        con_driver.type = 'SCRIPTED'

        for i in range(len(con_dict['name'])):
            con_var = con_driver.variables.new()
            con_var.name = con_dict['name'][i]
            con_var.targets[0].id_type = 'MESH'
            con_var.targets[0].id = bpy.data.meshes[track_name]
            con_var.targets[0].data_path = f"vertices[{index}].co[{con_dict['axis']}]"
        
        con_driver.expression = con_dict.get('expression')

    config_pos_x = {
        'name':['POS_X'],
        'data_path':['pose_x'],
        'data_type':'location',
        'expression': 'POS_X/1000',
        'axis':0
    }

    config_pos_y = {
        'name':['POS_Y'],
        'data_path':['pose_y'],
        'data_type':'location',
        'expression': 'POS_Y/1000',
        'axis':1
    }

    config_pos_z = {
        'name':['POS_Z'],
        'data_path':['pose_z'],
        'data_type':'location',
        'expression': 'POS_Z/1000',
        'axis':2
    }

    dri_config_location(dri_pos_x, config_pos_x)
    dri_config_location(dri_pos_y, config_pos_y)
    dri_config_location(dri_pos_z, config_pos_z)
    """

def normal_to_euler(nor):

    dx = 0
    dy = 0
    dz = 1

    dx_, dy_, dz_ = nor[0], nor[1], nor[2]

    # 计算点积
    dot_product = dx * dx_ + dy * dy_ + dz * dz_
    
    # 计算夹角
    angle = math.acos(dot_product)
    
    # 计算rx
    rx = math.atan2(dz_, math.sqrt(dx_**2 + dy_**2))
    
    # 计算ry
    ry = math.atan2(dy_, math.sqrt(dx_**2 + dz_**2))
    
    # 计算rz
    rz = math.atan2(dx_, math.sqrt(dy_**2 + dz_**2))

    return [rx, ry, rz]

def euler_to_normal(euler):
    x_euler = euler[0]
    y_euler = euler[1]
    z_euler = euler[2]
    # 初始向量 [0, 0, 1]
    
    # 计算旋转矩阵
    Rx = np.array([[1, 0, 0],
               [0, np.cos(x_euler), -np.sin(x_euler)],
               [0, np.sin(x_euler), np.cos(x_euler)]])

    # 绕y轴旋转的矩阵
    Ry = np.array([[np.cos(y_euler), 0, np.sin(y_euler)],
               [0, 1, 0],
               [-np.sin(y_euler), 0, np.cos(y_euler)]])

    Rz = np.array([[np.cos(z_euler), -np.sin(z_euler), 0],
                [np.sin(z_euler), np.cos(z_euler), 0],
                [0, 0, 1]])
    
    R = np.dot(np.dot(Rz, Ry), Rx)
    res = np.dot(R, np.transpose([0, 0, 1]))
    return list(res)

def normal_sim(tmp_path, traph):
    # 导入法线数据
    if not os.path.exists(os.path.join(tmp_path, 'tmp.json')):
        raise ValueError("请输入正确临时文件路径")
    '''
    if traph.track_name + '_surface' not in bpy.data.objects.keys() or traph.track_name + '_edge' not in bpy.data.objects.keys():
        raise ValueError("轨迹物体缺失，请检查")
    '''
    with open(os.path.join(tmp_path, 'tmp.json'), 'r') as f:
        tmp_data = json.load(f)
    
    c = []
    labels = tmp_data.keys()
    nor_data = []
    for label in labels:
        label_name = label.split('_')[-1]
        for point in tmp_data[label]:
            nor_data.append(point['n'])

        for i, vertice in enumerate(bpy.data.meshes[f'{traph.track_name}_{label_name}'].vertices):
            pos_cur = vertice.co
            # 换算
            euler_cur = nor_data[i]
            build_normal_obj(traph, pos_cur, euler_cur, i, f'{traph.track_name}_{label_name}')
    
    
    
class Normal_show(bpy.types.Operator):
    # 暂时整合入导入类，不进行单独operator
    bl_label='展示法线'
    bl_idname = 'obj.normalsim' # no da xie  
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        traph = context.scene.traph
        normal_sim(traph.output_path, traph.tmp_path, traph)
        return {'FINISHED'}
    
# -----------更新轨迹类&运行函数-----------

def write_obj(traph, path):
    if not os.path.exists(path):
        os.makedirs(path)
    pos_data = []
    nor_data = []

    # 从 data.meshes检查所拥有的labelname
    labels_name = []
    for mesh in bpy.data.meshes:
        if mesh.name.split('_')[0] == traph.track_name:
            labels_name.append(mesh.name.split('_')[-1])

    for label_name in labels_name:
        num = len(bpy.data.meshes[f'{traph.track_name}_{label_name}'].vertices)
        for i in range(num): 
            pos_data.append(bpy.data.objects[f'{traph.track_name}_{label_name}_{i}'].location)
            nor_data.append(bpy.data.objects[f'{traph.track_name}_{label_name}_{i}'].rotation_euler)

        with open(os.path.join(traph.tmp_path, 'tmp.json'), 'r') as f:
            tmp_data = json.load(f)

        obj_data = []

        for i in range(num):
            obj_data.append(
                {'p': pos_data[i],
                'n': nor_data[i],
                "speed": tmp_data[f'traj_{label_name}'][i]['speed'],
                "index": tmp_data[f'traj_{label_name}'][i]['index'],
                "spray": tmp_data[f'traj_{label_name}'][i]['spray']}
                )


        json2obj(obj_data, traph.tmp_path, f'{traph.track_name}_{labels_name}')

def track_update(traph, tmp_path):
    # 从data.meshes检查所拥有的labelname
    labels_name = []
    for mesh in bpy.data.meshes:
        if mesh.name.split('_')[0] == traph.track_name:
            labels_name.append(mesh.name.split('_')[-1]) # surface/edge

    for label_name in labels_name:
        
        obj_name = traph.track_name + '_' + label_name # example_surface

        if not os.path.exists(os.path.join(traph.tmp_path, 'tmp.json')):
            raise ValueError("临时文件缺失，请重新导入")
        """
        if traph.track_name + '_surface' not in bpy.data.objects.keys() or traph.track_name + '_edge' not in bpy.data.objects.keys():
            raise ValueError("轨迹物体缺失，请检查")
        """
        write_obj(traph, traph.tmp_path)
        
        # 重载obj数据
        bpy.data.objects.remove(bpy.data.objects[obj_name])

        bpy.data.meshes.remove(bpy.data.meshes[obj_name])


        bpy.ops.wm.obj_import(filepath=os.path.join(tmp_path, f'{traph.track_name}_{label_name}.obj'), directory=tmp_path, global_scale=1)
        init_trans(bpy.context.object)

        # 将轨迹本身设为不可选， 避免操作点时误选
        bpy.data.objects[f'{traph.track_name}_{label_name}'].hide_select = True


    


class Track_update(bpy.types.Operator):
    bl_label='更新轨迹'
    bl_idname = 'obj.trackupdate' # no da xie  
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        traph = context.scene.traph
        track_update(traph, traph.tmp_path)
        return {'FINISHED'}
    
# -----------导出轨迹类&运行函数-----------

def track_output(output_path, tmp_path, traph):
    if not os.path.exists(output_path):
        raise ValueError("请输入正确文件输出路径")
    if not os.path.exists(os.path.join(tmp_path, 'tmp.json')):
        raise ValueError("请输入正确临时文件路径") 
    # if traph.track_name + '_surface' not in bpy.data.objects.keys() or traph.track_name + '_edge' not in bpy.data.objects.keys():
        # raise ValueError("轨迹物体缺失，请检查")
    with open(os.path.join(tmp_path, 'tmp.json'), 'r') as f:
        tmp_data = json.load(f)
    output_data = {}
    # 从data.meshes搜索
    for key in bpy.data.meshes.keys():
        label_name = key.split('_')[-1]
        output_data = point_list_write(traph, f'{label_name}', tmp_data[f'traj_{label_name}'])

        output_data[f'traj_{label_name}'] = output_data

    with open(os.path.join(output_path, f'{traph.track_name}.json'), 'w') as f:
        json.dump(output_data, f)
        print("轨迹文件写入完成")




class Track_output(bpy.types.Operator):
    bl_label='导出轨迹'
    bl_idname = 'obj.trackoutput' # no da xie  
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        traph = context.scene.traph
        track_output(traph.output_path, traph.tmp_path, traph)
        return {'FINISHED'}


# -----------UI类-----------
class Track_ui(bpy.types.Panel):
    bl_idname = "Track_ui"
    bl_label = "轨迹管理工具"

    # 标签分类
    bl_category = "TRACK TOOL"

    # ui_type
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # bl_context = ["objectmode", 'posemode']

    def draw(self, context):
        layout = self.layout
        layout.label(text="轨迹文件管理", icon="TRACKING")

        col = layout.column()
        scene = context.scene.traph
        
        col.prop(scene, 'input_path', text="导入文件路径")
        col.prop(scene, 'tmp_path', text="临时文件路径")
        row = col.row(align=False)
        row.operator("obj.trackinput", text="导入轨迹",icon="IMPORT")
        row.prop(scene, 'clear_blend', text="重置工程数据")
        row = col.row(align=False)
        row.operator("obj.trackupdate", text="更新轨迹",icon="FILE_REFRESH")
        col.prop(scene, 'track_name', text='轨迹名称')
        

        col.prop(scene, 'output_path', text="导出文件路径")
        col.operator("obj.trackoutput", text="导出轨迹",icon="EXPORT")

def model_input(input_path, traph):

    # 单位强制设置为毫米
    bpy.context.scene.unit_settings.length_unit = 'MILLIMETERS'
    if not os.path.basename(input_path).endswith('.obj'):
        raise ValueError("请输入.obj文件")
    bpy.ops.wm.obj_import(filepath=input_path, directory=os.path.dirname(input_path), global_scale=0.001)
    init_trans(bpy.context.object)
    bpy.context.object.name = 'model'


class Model_input(bpy.types.Operator):
    # output bvh
    bl_label='导入轨迹'
    bl_idname = 'obj.modelinput' # no da xie
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        traph = context.scene.traph
        model_input(traph.input_path_model, traph)
        return {'FINISHED'}


class Model_ui(bpy.types.Panel):
    bl_idname = "Object_ui"
    bl_label = "模型管理工具"

    # 标签分类
    bl_category = "TRACK TOOL"

    # ui_type
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        layout.label(text="模型文件管理", icon="AUTO")

        col = layout.column()
        scene = context.scene.traph
        
        col.prop(scene, 'input_path_model', text="导入模型路径")
        row = col.row(align=False)
        row.operator("obj.modelinput", text="导入车模型",icon="IMPORT")

        
# RNA属性 在当前场景中命名为traph子类
class track_property(bpy.types.PropertyGroup):
    
    input_path: bpy.props.StringProperty(name='input_path',subtype='FILE_PATH')
    tmp_path: bpy.props.StringProperty(name='tmp_path',subtype='FILE_PATH')

    track_name: bpy.props.StringProperty(name='track_name')
    clear_blend: bpy.props.BoolProperty(name='clear_blend',default=True)

    output_path: bpy.props.StringProperty(name='output_path',subtype='FILE_PATH')

    input_path_model: bpy.props.StringProperty(name='input_path_model',subtype='FILE_PATH')
    
    
classGroup = [track_property,
              Track_ui,
              Track_input,
              Track_output,
              Track_update,
              Model_input,
              Model_ui
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
