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
        out vec3 position_world;
        out vec4 clip_space_position; // Position in clip space
        out vec3 eye_space_position; // Position in eye space

        void main() {
            vec4 world_position = vec4(position, 1.0);
            eye_space_position = (view * world_position).xyz;
            clip_space_position = projection * view * world_position;
            gl_Position = clip_space_position;
            position_world = position;
        }
        '''

        fragment_source = '''
        #version 330 core
        out vec4 out_color;
        uniform float time;
        uniform vec3 camera_position; // We'll need to pass this from Python
        in vec3 position_world;
        in vec4 clip_space_position;
        in vec3 eye_space_position;

        // Constants for water properties
        const vec3 WATER_COLOR = vec3(0.0, 0.3, 0.6); // Deep blue
        const float REFRACTIVE_INDEX_AIR = 1.0;
        const float REFRACTIVE_INDEX_WATER = 1.33;
        const float WAVE_STRENGTH = 0.02; // How strong the waves are
        const float WAVE_SPEED = 0.5; // How fast the waves move

        void main() {
            // Calculate normalized device coordinates
            vec3 ndc = clip_space_position.xyz / clip_space_position.w;
            vec2 screen_uv = ndc.xy * 0.5 + 0.5; // Convert to [0,1] range

            // Calculate view direction
            vec3 view_direction = normalize(camera_position - position_world);
            
            // Simple wave distortion
            float wave_offset_x = sin(position_world.x * 10.0 + time * WAVE_SPEED) * WAVE_STRENGTH;
            float wave_offset_z = cos(position_world.z * 10.0 + time * WAVE_SPEED) * WAVE_STRENGTH;
            vec3 normal = normalize(vec3(wave_offset_x, 1.0, wave_offset_z)); // Simple normal for waves

            // Fresnel effect
            float fresnel_factor = pow(1.0 - dot(view_direction, normal), 2.0);
            fresnel_factor = clamp(fresnel_factor, 0.1, 1.0); // Ensure some minimum reflection

            // Reflection (simplified: just a brighter version of water color)
            vec3 reflection_color = WATER_COLOR * 1.5; // Brighter for reflection

            // Refraction (simplified: just a darker version of water color)
            vec3 refraction_color = WATER_COLOR * 0.8; // Darker for refraction

            // Combine reflection and refraction based on Fresnel
            vec3 final_color = mix(refraction_color, reflection_color, fresnel_factor);

            // Add some subtle animation to the alpha
            float animated_alpha = 0.5 + sin(time * 0.5 + position_world.x * 0.1 + position_world.z * 0.1) * 0.1;
            animated_alpha = clamp(animated_alpha, 0.4, 0.6);

            out_color = vec4(final_color, animated_alpha);
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

    def draw(self, projection, view, time, camera_position):
        if self.program:
            pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
            pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
            pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE) # Disable culling for water
            self.program.use()
            self.program['projection'] = projection
            self.program['view'] = view
            self.program['time'] = time # Pass time uniform
            self.program['camera_position'] = camera_position # Pass camera position uniform
            self.vertex_list.draw(pyglet.gl.GL_TRIANGLES)
            self.program.stop()
            pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE) # Re-enable culling
            pyglet.gl.glDisable(pyglet.gl.GL_BLEND)