from typing import Optional

import bpy
import numpy as np

from ...shader_base import Nodes
from ..source2_shader_base import Source2ShaderBase


class DummyShader(Source2ShaderBase):
    SHADER: str = 'DUMMY'

    def create_nodes(self, material_name: str):
        if super().create_nodes(material_name) in ['UNKNOWN', 'LOADED']:
            return

        material_output = self.create_node(Nodes.ShaderNodeOutputMaterial)
        shader = self.create_node(Nodes.ShaderNodeBsdfPrincipled, self.SHADER)
        self.connect_nodes(shader.outputs['BSDF'], material_output.inputs['Surface'])
        data, = self._material_resource.get_data_block(block_name='DATA')
        if data:
            for param in data['m_textureParams']:
                texture_path = self._material_resource.get_texture_property(param['m_name'], None)
                if texture_path is not None:
                    image = self.load_texture_or_default(texture_path, (1.0, 1.0, 1.0, 1.0))
                    self.create_texture_node(image, param['m_name'])