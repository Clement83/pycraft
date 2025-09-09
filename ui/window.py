import math
import pyglet
from pyglet.graphics import shader
from pyglet.window import key
from pyglet.math import Mat4, Vec3

from core.world import World
from core.player import Player, EYE_HEIGHT
from core.water import WaterPlane



class GhostCamera:
    def __init__(self, window):
        self.window = window
        self.projection = Mat4.perspective_projection(
            aspect=window.width / window.height, 
            z_near=0.1, 
            z_far=4000.0, 
            fov=65.0
        )
        self.view = Mat4()

    def update(self, player):
        """Met à jour la matrice de vue basée sur la position et rotation du joueur"""
        # Position de la caméra = position du joueur
        pos = Vec3(player.position[0], player.position[1] + EYE_HEIGHT, player.position[2])
        
        # Calculer le point vers lequel on regarde
        pitch_rad = math.radians(player.pitch)
        yaw_rad = math.radians(player.yaw)
        
        look_x = pos.x + math.sin(yaw_rad) * math.cos(pitch_rad)
        look_y = pos.y - math.sin(pitch_rad)
        look_z = pos.z - math.cos(yaw_rad) * math.cos(pitch_rad)
        
        look_at = Vec3(look_x, look_y, look_z)
        up = Vec3(0, 1, 0)
        
        # Créer la matrice de vue avec lookAt
        self.view = Mat4.look_at(pos, look_at, up)

    def on_resize(self, width, height):
        """Met à jour la projection lors du redimensionnement"""
        self.projection = Mat4.perspective_projection(
            aspect=width / height, 
            z_near=0.1, 
            z_far=4000.0, 
            fov=65.0
        )

# Classe Window mise à jour pour utiliser le nouveau système
class Window(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_minimum_size(300, 200)
        
        # OpenGL context
        pyglet.gl.glClearColor(0.5, 0.7, 1.0, 1.0)
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glFrontFace(pyglet.gl.GL_CCW)
        pyglet.gl.glDepthFunc(pyglet.gl.GL_LESS)

        # Initialisation du système fantôme
        self.player = Player((0, 2, 0))
        self.camera = GhostCamera(self)
        
        # Shader program (votre code existant)
        self.program = self.create_shader_program()
        self.world = World(self.program)
        self.water = WaterPlane(size=2000.0)  # Votre eau existante
        
        # Underwater filter initialization
        self.underwater_program = self.create_underwater_shader_program()
        if self.underwater_program:
            # Create a full-screen quad for the underwater effect
            # Vertices are in clip space [-1, 1]
            underwater_vertices = [
                -1.0, -1.0,
                 1.0, -1.0,
                 1.0,  1.0,
                -1.0,  1.0
            ]
            underwater_indices = [0, 1, 2, 0, 2, 3]
            self.underwater_vertex_list = self.underwater_program.vertex_list_indexed(
                4, pyglet.gl.GL_TRIANGLES, underwater_indices,
                position=('f', underwater_vertices)
            )
        else:
            self.underwater_vertex_list = None

        # Blit shader program for drawing FBO texture to screen when not underwater
        self.blit_program = self.create_blit_shader_program()
        if self.blit_program:
            # Re-use the underwater_vertex_list as it's a simple full-screen quad
            self.blit_vertex_list = self.underwater_vertex_list
        else:
            self.blit_vertex_list = None

        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        pyglet.clock.schedule(self.update)
        self.set_exclusive_mouse(True)

        # UI
        self.ui_batch = pyglet.graphics.Batch()
        self.info_label = pyglet.text.Label(
            '',
            font_name='Arial',
            font_size=12,
            x=5, y=self.height - 5,
            anchor_x='left', anchor_y='top',
            batch=self.ui_batch
        )
        self.mode_label = pyglet.text.Label(
            '',
            font_name='Arial',
            font_size=12,
            x=5, y=self.height - 25,
            anchor_x='left', anchor_y='top',
            batch=self.ui_batch
        )
        self.debug_label = pyglet.text.Label(
            '',
            font_name='Arial',
            font_size=12,
            x=5, y=self.height - 45,
            anchor_x='left', anchor_y='top',
            batch=self.ui_batch
        )
        self.total_time = 0.0 # Initialize total time

        # Framebuffer Object (FBO) for post-processing
        self.fbo = pyglet.gl.GLuint() # Create a GLuint object to store the FBO ID
        pyglet.gl.glGenFramebuffers(1, self.fbo) # Generate 1 framebuffer and store its ID in self.fbo

        self.fbo_texture = pyglet.gl.GLuint() # Create a GLuint object for the texture ID
        pyglet.gl.glGenTextures(1, self.fbo_texture) # Generate 1 texture and store its ID

        self.fbo_depth_texture = pyglet.gl.GLuint() # Create a GLuint object for the depth texture ID
        pyglet.gl.glGenTextures(1, self.fbo_depth_texture) # Generate 1 texture and store its ID

        self.create_fbo_attachments(self.width, self.height)

    def create_shader_program(self):
        vertex_shader_source = '''
        #version 330 core
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec2 tex_coords;
        layout (location = 2) in vec3 colors;

        out vec2 new_tex_coords;
        out vec3 new_colors;

        uniform mat4 projection;
        uniform mat4 view;

        void main()
        {
            gl_Position = projection * view * vec4(position, 1.0);
            new_tex_coords = tex_coords;
            new_colors = colors;
        }
        '''
        fragment_shader_source = '''
        #version 330 core
        in vec2 new_tex_coords;
        in vec3 new_colors;

        out vec4 out_color;

        uniform sampler2D our_texture;

        void main()
        {
            out_color = texture(our_texture, new_tex_coords);
            if(out_color.a < 0.1)
                discard;
            out_color *= vec4(new_colors, 1.0);
        }
        '''
        try:
            vert_shader = shader.Shader(vertex_shader_source, 'vertex')
            frag_shader = shader.Shader(fragment_shader_source, 'fragment')
            return shader.ShaderProgram(vert_shader, frag_shader)
        except shader.ShaderException as e:
            print(e)
            pyglet.app.exit()
            return None

    def create_underwater_shader_program(self):
        vertex_shader_source = '''
        #version 330 core
        layout (location = 0) in vec2 position;
        out vec2 uv;

        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
            uv = (position + 1.0) * 0.5; // Convert from [-1,1] to [0,1]
        }
        '''
        fragment_shader_source = '''
        #version 330 core
        in vec2 uv;
        out vec4 out_color;
        uniform float time;
        uniform vec2 resolution;
        uniform sampler2D scene_texture; // The FBO texture

        void main() {
            vec2 distorted_uv = uv;
            // Simple distortion based on time and UV, scaled by resolution
            float distortion_strength = 0.01 * (1000.0 / resolution.x); // Original distortion strength
            distorted_uv.x += sin(uv.y * 10.0 + time * 2.0) * distortion_strength;
            distorted_uv.y += cos(uv.x * 10.0 + time * 2.0) * distortion_strength;

            // Sample the scene texture with distorted UVs
            vec4 scene_color = texture(scene_texture, distorted_uv);

            // Apply a blue tint and alpha
            vec4 underwater_color = vec4(0.0, 0.3, 0.6, 0.7);

            // Make alpha pulsate slightly with time
            float alpha_pulsation = sin(time * 3.0) * 0.05 + 0.95; // Varies between 0.9 and 1.0
            underwater_color.a *= alpha_pulsation;

            // Combine scene color with underwater tint
            out_color = mix(scene_color, underwater_color, underwater_color.a);
        }
        '''
        try:
            vert_shader = shader.Shader(vertex_shader_source, 'vertex')
            frag_shader = shader.Shader(fragment_shader_source, 'fragment')
            return shader.ShaderProgram(vert_shader, frag_shader)
        except shader.ShaderException as e:
            print(e)
            pyglet.app.exit()
            return None

    def create_blit_shader_program(self):
        vertex_shader_source = '''
        #version 330 core
        layout (location = 0) in vec2 position;
        out vec2 uv;

        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
            uv = (position + 1.0) * 0.5; // Convert from [-1,1] to [0,1]
        }
        '''
        fragment_shader_source = '''
        #version 330 core
        in vec2 uv;
        out vec4 out_color;
        uniform sampler2D screen_texture;

        void main() {
            out_color = texture(screen_texture, uv);
        }
        '''
        try:
            vert_shader = shader.Shader(vertex_shader_source, 'vertex')
            frag_shader = shader.Shader(fragment_shader_source, 'fragment')
            return shader.ShaderProgram(vert_shader, frag_shader)
        except shader.ShaderException as e:
            print(e)
            pyglet.app.exit()
            return None

    def create_fbo_attachments(self, width, height):
        # Bind FBO
        pyglet.gl.glBindFramebuffer(pyglet.gl.GL_FRAMEBUFFER, self.fbo)

        # Color attachment
        pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self.fbo_texture)
        pyglet.gl.glTexImage2D(pyglet.gl.GL_TEXTURE_2D, 0, pyglet.gl.GL_RGB, width, height, 0, pyglet.gl.GL_RGB, pyglet.gl.GL_UNSIGNED_BYTE, None)
        pyglet.gl.glTexParameteri(pyglet.gl.GL_TEXTURE_2D, pyglet.gl.GL_TEXTURE_MIN_FILTER, pyglet.gl.GL_LINEAR)
        pyglet.gl.glTexParameteri(pyglet.gl.GL_TEXTURE_2D, pyglet.gl.GL_TEXTURE_MAG_FILTER, pyglet.gl.GL_LINEAR)
        pyglet.gl.glFramebufferTexture2D(pyglet.gl.GL_FRAMEBUFFER, pyglet.gl.GL_COLOR_ATTACHMENT0, pyglet.gl.GL_TEXTURE_2D, self.fbo_texture, 0)

        # Depth attachment
        pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self.fbo_depth_texture)
        pyglet.gl.glTexImage2D(pyglet.gl.GL_TEXTURE_2D, 0, pyglet.gl.GL_DEPTH_COMPONENT, width, height, 0, pyglet.gl.GL_DEPTH_COMPONENT, pyglet.gl.GL_FLOAT, None)
        pyglet.gl.glFramebufferTexture2D(pyglet.gl.GL_FRAMEBUFFER, pyglet.gl.GL_DEPTH_ATTACHMENT, pyglet.gl.GL_TEXTURE_2D, self.fbo_depth_texture, 0)

        # Check FBO completeness
        if pyglet.gl.glCheckFramebufferStatus(pyglet.gl.GL_FRAMEBUFFER) != pyglet.gl.GL_FRAMEBUFFER_COMPLETE:
            print("ERROR::FRAMEBUFFER:: Framebuffer is not complete!")

        # Unbind FBO
        pyglet.gl.glBindFramebuffer(pyglet.gl.GL_FRAMEBUFFER, 0)

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.camera.on_resize(width, height)
        self.create_fbo_attachments(width, height) # Update FBO attachments on resize

    def on_mouse_motion(self, x, y, dx, dy):
        # Sensibilité de la souris
        sensitivity = 0.15
        self.player.rotate(-dy * sensitivity, dx * sensitivity)

    def update(self, dt):
        self.total_time += dt # Update total time
        self.player.update(dt, self.keys, self.world)
        self.camera.update(self.player)
        
        # Mettre à jour l'affichage de position
        pos = self.player.position
        self.info_label.text = f'Position: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) | Pitch: {self.player.pitch:.1f}° | Yaw: {self.player.yaw:.1f}°'
        mode_text = f"Mode: {'Ghost' if self.player.ghost_mode else 'Grounded'}"
        if self.player.is_swimming:
            mode_text += " (Swimming)"
        self.mode_label.text = mode_text
        self.debug_label.text = self.player.debug_info
        
        # Mettre à jour votre monde si vous l'avez
        self.world.update(self.player.position)

    def on_draw(self):
        # Render to FBO
        pyglet.gl.glBindFramebuffer(pyglet.gl.GL_FRAMEBUFFER, self.fbo)
        self.clear() # Clear FBO

        # Rendu 3D
        self.program.use()
        self.program['projection'] = self.camera.projection
        self.program['view'] = self.camera.view

        self.world.draw(self.player.position)

        self.program.stop()
        
        # Dessiner votre eau si vous l'avez
        self.water.draw(self.camera.projection, self.camera.view, self.total_time, self.player.position)
        
        # Unbind FBO and render to screen
        pyglet.gl.glBindFramebuffer(pyglet.gl.GL_FRAMEBUFFER, 0)
        self.clear() # Clear screen

        # Appliquer le filtre sous-marin si le joueur est sous l'eau
        if self.player.is_swimming:
            self.draw_underwater_filter()
        else:
            # If not underwater, draw the FBO texture directly to screen using the blit shader
            if self.blit_program and self.blit_vertex_list:
                pyglet.gl.glDisable(pyglet.gl.GL_BLEND) # Disable blending for full screen quad
                
                self.blit_program.use()
                pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
                pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self.fbo_texture)
                self.blit_program['screen_texture'] = 0 # Assign texture unit 0
                
                self.blit_vertex_list.draw(pyglet.gl.GL_TRIANGLES)
                self.blit_program.stop()

        # UI
        self.ui_batch.draw()

    def draw_underwater_filter(self):
        if self.underwater_program and self.underwater_vertex_list:
            pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
            pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
            
            self.underwater_program.use()
            self.underwater_program['time'] = self.total_time
            self.underwater_program['resolution'] = (float(self.width), float(self.height))
            
            # Pass the FBO texture as a uniform
            pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
            pyglet.gl.glBindTexture(pyglet.gl.GL_TEXTURE_2D, self.fbo_texture)
            self.underwater_program['scene_texture'] = 0 # Assign texture unit 0
            
            self.underwater_vertex_list.draw(pyglet.gl.GL_TRIANGLES)
            self.underwater_program.stop()
            
            pyglet.gl.glDisable(pyglet.gl.GL_BLEND)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            pyglet.app.exit()
        elif symbol == key.T:
            self.player.toggle_ghost_mode()

    def run(self):
        pyglet.app.run()