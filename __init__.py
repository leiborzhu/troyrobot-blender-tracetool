bl_info = {
    "name": "track_tool",
    "author": "zhuhe",
    "version": (0, 8, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar >Trace manage",
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
    for point in list_data:
        index = point['index']
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
    line_lines.append(f"l {num-1} 1\n") # 当前默认轨迹首尾相连

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


    # 单位强制设置为毫米
    bpy.context.scene.unit_settings.length_unit = 'MILLIMETERS'

    filepath = input_path
    file_name = input_path.split('\\')[-1]
    directory = file_name.strip(file_name)
    if not file_name.endswith('.json'):
        raise ValueError("请输入正确的json文件路径")
    if not directory.startswith(os.path.abspath(__file__)):
        directory = os.path.join(os.path.abspath(__file__), directory)

    if not os.path.exists(tmp_path):
        raise ValueError("请输入正确的临时文件放置路径")
    
    if traph.clear_blend:
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh, do_unlink=True)
        for material in bpy.data.materials:
            bpy.data.materials.remove(material, do_unlink=True)

    # bpy.ops.wm.obj_import(filepath=filepath, directory=directory)
        
    # 读取json文件
    with open(filepath, 'r') as f:
        raw_data = json.load(f)
    traj_surface = raw_data['traj_surface']
    traj_edge = raw_data['traj_edge']

    raw_name = file_name.split('.')[0]
    json2obj(traj_surface, tmp_path, f'{raw_name}_surface')
    json2obj(traj_edge, tmp_path, f'{raw_name}_edge')

    # 导入obj文件
    bpy.ops.wm.obj_import(filepath=os.path.join(tmp_path, f'{raw_name}_surface.obj'), directory=tmp_path, global_scale=0.001)
    init_trans(bpy.context.object)
    bpy.ops.wm.obj_import(filepath=os.path.join(tmp_path, f'{raw_name}_edge.obj'), directory=tmp_path, global_scale=0.001)
    init_trans(bpy.context.object)
    traph.track_name = raw_name

    # bpy.ops.wm.obj_import(filepath="input_path")
    # 处理speed, spary等其他信息
    # TODO: 目前没有blender合适自定义property承载这些信息，先利用tmp.json文件的形式处理

    tmp_traj_surface = []
    tmp_traj_edge = []
    for point in traj_surface:
        tmp_traj_surface.append({'speed': point['speed'], 'spray': point['spray'], 'index': point['index'], 'n': point['n']})
    for point in traj_edge:
        tmp_traj_edge.append({'speed': point['speed'], 'spray': point['spray'], 'index': point['index'], 'n': point['n']})

    tmp_data = {
        'traj_surface': tmp_traj_surface,
        'traj_edge': tmp_traj_edge
    }

    with open(os.path.join(tmp_path, 'tmp.json'), 'w') as f:
        json.dump(tmp_data, f)
        print("临时数据写入完成")

    # 添加轴空物体
    normal_sim(tmp_path, traph)

    # 将轨迹本身设为不可选， 避免操作点时误选
    bpy.data.objects[traph.track_name + '_surface'].hide_select = True
    bpy.data.objects[traph.track_name + '_edge'].hide_select = True


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
    scale = 1 # 单位强制设置为毫米，此处scale为1000
    point_list = []
    pos_list = []
    nor_list = []
    num = len(bpy.data.meshes[traph.track_name + '_' + label].vertices) # example_name
    for i in range(num):
        obj = bpy.data.objects[traph.track_name + '_' + label + '_' + str(i)] # example_name_0

        pos_list.append(obj.location)
        # 弧度制 默认XYZ
        nor_list.append([obj.rotation_euler[0], obj.rotation_euler[1], obj.rotation_euler[2]])



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


def normal_sim(tmp_path, traph):
    # 导入法线数据
    if not os.path.exists(os.path.join(tmp_path, 'tmp.json')):
        raise ValueError("请输入正确临时文件路径")
    if traph.track_name + '_surface' not in bpy.data.objects.keys() or traph.track_name + '_edge' not in bpy.data.objects.keys():
        raise ValueError("轨迹物体缺失，请检查")
    
    with open(os.path.join(tmp_path, 'tmp.json'), 'r') as f:
        tmp_data = json.load(f)
    
    nor_surface = []
    nor_edge = []

    for point in tmp_data['traj_surface']:
        nor_surface.append(point['n'])
    for point in tmp_data['traj_edge']:
        nor_edge.append(point['n'])

    for i, vertice in enumerate(bpy.data.meshes[traph.track_name + '_surface'].vertices):
        pos_cur = vertice.co
        nor_cur = nor_surface[i]
        build_normal_obj(traph, pos_cur, nor_cur, i, traph.track_name + '_surface')
        
    for i, vertice in enumerate(bpy.data.meshes[traph.track_name + '_edge'].vertices):
        pos_cur = vertice.co
        nor_cur = nor_edge[i]
        build_normal_obj(traph, pos_cur, nor_cur, i, traph.track_name + '_edge')
    
    
    
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
    pos_surface = []
    pos_edge = []
    nor_surface = []
    nor_edge = []
    num_surface = len(bpy.data.meshes[traph.track_name + '_surface'].vertices)
    num_edge = len(bpy.data.meshes[traph.track_name + '_edge'].vertices)
    for i in range(num_surface): 
        pos_surface.append(bpy.data.objects[f'{traph.track_name}_surface_{i}'].location)
        nor_surface.append(bpy.data.objects[f'{traph.track_name}_surface_{i}'].rotation_euler)
    
    for i in range(num_edge): 
        pos_edge.append(bpy.data.objects[f'{traph.track_name}_edge_{i}'].location)
        nor_edge.append(bpy.data.objects[f'{traph.track_name}_edge_{i}'].rotation_euler)

    with open(os.path.join(traph.tmp_path, 'tmp.json'), 'r') as f:
        tmp_data = json.load(f)

    obj_data_surface = []
    obj_data_edge = []

    for i in range(num_surface):
        obj_data_surface.append(
            {'p': pos_surface[i],
            'n': nor_surface[i],
            "speed": tmp_data['traj_surface'][i]['speed'],
            "index": tmp_data['traj_surface'][i]['index'],
            "spray": tmp_data['traj_surface'][i]['spray']}
            )
    for i in range(num_edge):
        obj_data_edge.append(
            {'p': pos_edge[i],
            'n': nor_edge[i],
            "speed": tmp_data['traj_edge'][i]['speed'],
            "index": tmp_data['traj_edge'][i]['index'],
            "spray": tmp_data['traj_edge'][i]['spray']}
            )

    json2obj(obj_data_surface, traph.tmp_path, f'{traph.track_name}_surface')
    json2obj(obj_data_edge, traph.tmp_path, f'{traph.track_name}_edge')

def track_update(traph, tmp_path):

    surface_name = traph.track_name + '_surface' # example_surface
    edge_name = traph.track_name + '_edge'

    if not os.path.exists(os.path.join(traph.tmp_path, 'tmp.json')):
        raise ValueError("请输入正确临时文件路径")
    if traph.track_name + '_surface' not in bpy.data.objects.keys() or traph.track_name + '_edge' not in bpy.data.objects.keys():
        raise ValueError("轨迹物体缺失，请检查")
    write_obj(traph, traph.tmp_path)
    
    # 重载obj数据
    bpy.data.objects.remove(bpy.data.objects[surface_name])
    bpy.data.objects.remove(bpy.data.objects[edge_name])
    bpy.data.meshes.remove(bpy.data.meshes[surface_name])
    bpy.data.meshes.remove(bpy.data.meshes[edge_name])

    bpy.ops.wm.obj_import(filepath=os.path.join(tmp_path, f'{traph.track_name}_surface.obj'), directory=tmp_path, global_scale=1)
    init_trans(bpy.context.object)
    bpy.ops.wm.obj_import(filepath=os.path.join(tmp_path, f'{traph.track_name}_edge.obj'), directory=tmp_path, global_scale=1)
    init_trans(bpy.context.object)

    


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
    if traph.track_name + '_surface' not in bpy.data.objects.keys() or traph.track_name + '_edge' not in bpy.data.objects.keys():
        raise ValueError("轨迹物体缺失，请检查")
    with open(os.path.join(tmp_path, 'tmp.json'), 'r') as f:
        tmp_data = json.load(f)
    output_surface_data = point_list_write(traph, 'surface', tmp_data['traj_surface'])
    output_edge_data = point_list_write(traph, 'edge', tmp_data['traj_edge'])

    output_data = {
        'traj_surface': output_surface_data,
        'traj_edge': output_edge_data
    }

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
        layout.label(text="轨迹文件路径", icon="TRACKING")

        col = layout.column()
        scene = context.scene.traph
        
        col.prop(scene, 'input_path', text="导入文件路径")
        col.prop(scene, 'tmp_path', text="临时文件路径")
        row = col.row(align=False)
        row.operator("obj.trackinput", text="导入",icon="IMPORT")
        row.prop(scene, 'clear_blend', text="重置工程数据")
        row = col.row(align=False)
        row.operator("obj.trackupdate", text="更新轨迹",icon="FILE_REFRESH")
        col.prop(scene, 'track_name', text='轨迹名称')
        

        col.prop(scene, 'output_path', text="导出文件路径")
        col.operator("obj.trackoutput", text="导出",icon="EXPORT")

# RNA属性 在当前场景中命名为traph子类
class track_property(bpy.types.PropertyGroup):
    
    input_path: bpy.props.StringProperty(name='input_path',subtype='FILE_PATH')
    tmp_path: bpy.props.StringProperty(name='tmp_path',subtype='FILE_PATH')

    track_name: bpy.props.StringProperty(name='track_name')
    clear_blend: bpy.props.BoolProperty(name='clear_blend',default=True)

    output_path: bpy.props.StringProperty(name='output_path',subtype='FILE_PATH')
    
    
classGroup = [track_property,
              Track_ui,
              Track_input,
              Track_output,
              Track_update
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
