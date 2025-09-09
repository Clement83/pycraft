import pyglet
from pyglet.graphics import shader
from pyglet.math import Mat4

class WaterPlane:
    def __init__(self, height=0.0, size=200.0):
        self.height = height
        self.size = size
        s = self.size / 2
        h = self.height

        # Vertex data for a quad
        self.vertices = [
            -s, h, -s,
            -s, h,  s,
             s, h,  s,
             s, h, -s
        ]
        indices = [0, 1, 2, 0, 2, 3]

        # Create a simple shader for the water
        vertex_source = '''
        #version 330 core
        in vec3 position;
        uniform mat4 projection;
        uniform mat4 view;

        void main() {
            gl_Position = projection * view * vec4(position, 1.0);
        }
        '''

        fragment_source = '''
        #version 330 core
        out vec4 out_color;

        void main() {
            out_color = vec4(0.0, 0.3, 0.6, 0.5); // Semi-transparent blue
        }
        '''
        try:
            vert_shader = shader.Shader(vertex_source, 'vertex')
            frag_shader = shader.Shader(fragment_source, 'fragment')
            self.program = shader.ShaderProgram(vert_shader, frag_shader)
        except shader.ShaderException as e:
            print(e)
            # Handle shader compilation error
            self.program = None

        if self.program:
            self.vertex_list = self.program.vertex_list_indexed(4, pyglet.gl.GL_TRIANGLES, indices, position=('f', self.vertices))

    def draw(self, projection, view):
        if self.program:
            pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
            pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
            pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE) # Disable culling for water
            self.program.use()
            self.program['projection'] = projection
            self.program['view'] = view
            self.vertex_list.draw(pyglet.gl.GL_TRIANGLES)
            self.program.stop()
            pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE) # Re-enable culling
            pyglet.gl.glDisable(pyglet.gl.GL_BLEND)