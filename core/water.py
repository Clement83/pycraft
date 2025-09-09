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
        uniform float time; // Need to pass time to vertex shader
        uniform vec3 camera_position; // Player's position for centering the water plane
        out vec3 position_world;
        out vec4 clip_space_position; // Position in clip space
        out vec3 eye_space_position; // Position in eye space

        // Constants for wave properties (can be passed as uniforms or defined here)
        const float VERTEX_WAVE_STRENGTH = 0.1; // How much vertices are displaced vertically
        const float VERTEX_WAVE_FREQUENCY = 0.5; // How frequent the waves are
        const float VERTEX_WAVE_SPEED = 1.0; // How fast the waves move

        void main() {
            vec3 displaced_position = position;
            // Displace y-coordinate based on sine waves
            displaced_position.y += sin(position.x * VERTEX_WAVE_FREQUENCY + time * VERTEX_WAVE_SPEED) * VERTEX_WAVE_STRENGTH;
            displaced_position.y += cos(position.z * VERTEX_WAVE_FREQUENCY * 1.2 + time * VERTEX_WAVE_SPEED * 0.8) * (VERTEX_WAVE_STRENGTH * 0.7);

            // Center the water plane on the player's XZ coordinates
            displaced_position.xz += camera_position.xz;

            vec4 world_position = vec4(displaced_position, 1.0);
            eye_space_position = (view * world_position).xyz;
            clip_space_position = projection * view * world_position;
            gl_Position = clip_space_position;
            position_world = displaced_position; // Pass displaced position to fragment shader
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
        const float WAVE_STRENGTH = 0.05; // How strong the waves are
        const float WAVE_SPEED = 0.5; // How fast the waves move

        // Fog uniforms
        uniform vec3 fog_color;
        uniform float fog_start;
        uniform float fog_end;

        void main() {
            // Calculate normalized device coordinates
            vec3 ndc = clip_space_position.xyz / clip_space_position.w;
            vec2 screen_uv = ndc.xy * 0.5 + 0.5; // Convert to [0,1] range

            // Calculate view direction
            vec3 view_direction = normalize(camera_position - position_world);
            
            // Simple wave distortion
            float wave_offset_x = sin(position_world.x * 10.0 + time * WAVE_SPEED) * WAVE_STRENGTH;
            wave_offset_x += cos(position_world.z * 15.0 + time * WAVE_SPEED * 1.5) * (WAVE_STRENGTH * 0.5); // Added another wave for complexity
            float wave_offset_z = cos(position_world.z * 10.0 + time * WAVE_SPEED) * WAVE_STRENGTH;
            wave_offset_z += sin(position_world.x * 12.0 + time * WAVE_SPEED * 1.2) * (WAVE_STRENGTH * 0.4); // Added another wave for complexity
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

            // Apply fog
            float dist = length(eye_space_position); // Distance from camera to fragment in eye space
            float fog_factor = clamp((fog_end - dist) / (fog_end - fog_start), 0.0, 1.0);
            out_color = mix(vec4(fog_color, 1.0), out_color, fog_factor);
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

    def draw(self, projection, view, time, camera_position, fog_color, fog_start, fog_end):
        if self.program:
            pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
            pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
            pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE) # Disable culling for water
            self.program.use()
            self.program['projection'] = projection
            self.program['view'] = view
            self.program['time'] = time # Pass time uniform to vertex shader
            self.program['camera_position'] = camera_position # Pass camera position uniform
            self.program['fog_color'] = fog_color
            self.program['fog_start'] = fog_start
            self.program['fog_end'] = fog_end
            self.vertex_list.draw(pyglet.gl.GL_TRIANGLES)
            self.program.stop()
            pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE) # Re-enable culling
            pyglet.gl.glDisable(pyglet.gl.GL_BLEND)