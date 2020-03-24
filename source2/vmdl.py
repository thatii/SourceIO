import os.path
import sys

from .source2 import ValveFile
from .vmesh import Vmesh
import bpy, mathutils
from mathutils import Vector, Matrix, Euler, Quaternion
from .blocks.vbib_block import VBIB


class Vmdl:

    def __init__(self, vmdl_path, import_meshes):
        self.valve_file = ValveFile(vmdl_path)
        self.valve_file.read_block_info()
        self.valve_file.check_external_resources()

        self.name = str(os.path.basename(vmdl_path).split('.')[0])
        # print(self.valve_file.data.data.keys())
        self.remap_table = self.valve_file.data.data['m_remappingTable']
        self.model_skeleton = self.valve_file.data.data['m_modelSkeleton']
        self.bone_names = self.model_skeleton['m_boneName']
        self.bone_positions = self.model_skeleton['m_bonePosParent']
        self.bone_rotations = self.model_skeleton['m_boneRotParent']
        self.bone_parents = self.model_skeleton['m_nParent']
        self.main_collection = bpy.data.collections.new(os.path.basename(self.name))
        bpy.context.scene.collection.children.link(self.main_collection)

        # for res, path in self.valve_file.available_resources.items():
        #     if 'vmesh' in res and import_meshes:
        #         vmesh = Vmesh(path)
        #         vmesh.build_meshes(self.main_collection, self.bone_names, self.remap_table)
        self.build_meshes(self.main_collection)
        self.build_armature()

    def build_meshes(self, collection, bone_list=None, remap_list=None, ):
        for mdat, mbuf in self.valve_file.mdat:
            for scene in mdat.data["m_sceneObjects"]:
                draw_calls = scene["m_drawCalls"]
                for draw_call in draw_calls:
                    base_vertex = draw_call['m_nBaseVertex']
                    vertex_count = draw_call['m_nVertexCount']
                    start_index = draw_call['m_nStartIndex']
                    index_count = draw_call['m_nIndexCount']
                    index_buffer = mbuf.index_buffer[draw_call['m_indexBuffer']['m_hBuffer']]
                    assert len(draw_call['m_vertexBuffers']) == 1
                    # assert draw_call['m_vertexBuffers'][0]['m_bBindOffsetBytes'] == 0
                    assert draw_call['m_nStartInstance'] == 0
                    assert draw_call['m_nInstanceCount'] == 0
                    vertex_buffer = mbuf.vertex_buffer[draw_call['m_vertexBuffers'][0]['m_hBuffer']]
                    mesh_name = draw_call['m_material'].split("/")[0].split(".")[0]

                    mesh_obj = bpy.data.objects.new(mesh_name, bpy.data.meshes.new(mesh_name))
                    collection.objects.link(mesh_obj)
                    # bones = [bone_list[i] for i in remap_list]
                    mesh = mesh_obj.data
                    if bone_list:
                        print('Bone list available, creating vertex groups')
                        weight_groups = {bone: mesh_obj.vertex_groups.new(name=bone) for bone in
                                         bone_list}
                    vertexes = []
                    uvs = []
                    normals = []
                    # Extracting vertex coordinates,UVs and normals

                    for vertex in vertex_buffer.vertexes[base_vertex:base_vertex + vertex_count]:
                        vertexes.append(vertex.position.as_list)
                        uvs.append([vertex.uv.x, vertex.uv.y])
                        # vertex.normal.convert()
                    for poly in index_buffer.indexes[start_index:start_index + index_count]:
                        for v in poly:
                            normals.append(vertex_buffer.vertexes[v].normal.as_list)

                    mesh.from_pydata(vertexes, [], index_buffer.indexes[start_index:start_index + index_count])
                    mesh.update()
                    mesh.uv_layers.new()

                    uv_data = mesh.uv_layers[0].data
                    for i in range(len(uv_data)):
                        u = uvs[mesh.loops[i].vertex_index]
                        uv_data[i].uv = u
                    if bone_list:
                        for n, vertex in enumerate(vertex_buffer.vertexes[base_vertex:base_vertex + vertex_count]):
                            for bone_index, weight in zip(vertex.boneWeight.bone, vertex.boneWeight.weight):
                                if weight > 0:
                                    bone_name = bone_list[remap_list[bone_index]]
                                    weight_groups[bone_name].add([n], weight, 'REPLACE')
                    bpy.ops.object.shade_smooth()
                    mesh.normals_split_custom_set(normals)
                    mesh.use_auto_smooth = True

    def build_armature(self):

        bpy.ops.object.armature_add(enter_editmode=True)

        self.armature_obj = bpy.context.object
        # bpy.context.scene.collection.objects.unlink(self.armature_obj)
        self.main_collection.objects.link(self.armature_obj)
        self.armature = self.armature_obj.data
        self.armature.name = self.name + "_ARM"
        self.armature.edit_bones.remove(self.armature.edit_bones[0])

        bpy.ops.object.mode_set(mode='EDIT')
        bones = []
        for se_bone in self.bone_names:  # type:
            bones.append((self.armature.edit_bones.new(se_bone), se_bone))

        for n, (bl_bone, se_bone) in enumerate(bones):
            bone_pos = self.bone_positions[n]
            if self.bone_parents[n] != -1:
                bl_parent, parent = bones[self.bone_parents[n]]
                bl_bone.parent = bl_parent
                bl_bone.tail = Vector([0, 0, 0]) + bl_bone.head
                bl_bone.head = Vector(bone_pos.as_list) - bl_parent.head  # + bl_bone.head
                bl_bone.tail = bl_bone.head + Vector([0, 0, 1])
            else:
                pass
                bl_bone.tail = Vector([0, 0, 0]) + bl_bone.head
                bl_bone.head = Vector(bone_pos.as_list)  # + bl_bone.head
                bl_bone.tail = bl_bone.head + Vector([0, 0, 1])
        bpy.ops.object.mode_set(mode='OBJECT')


if __name__ == '__main__':
    a = Vmdl(r'E:\PYTHON\io_mesh_SourceMDL/test_data/source2/sniper.vmdl_c', True)