import math
import pyglet
from pyglet.graphics import shader
from pyglet.window import key, mouse
from pyglet.math import Mat4, Vec3
from pyglet import shapes
from enum import Enum

from core.world import World
from core.player import Player, EYE_HEIGHT
from core.player_sprite import PlayerSprite
from core.water import WaterPlane
from ui.hud import HUD
from ui.menu import Menu
from core.server import Server
from core.client import Client
import config
from ui.minimap import Minimap


class GameState(Enum):
    MENU = 1
    GAME = 2



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

        self.game_state = GameState.MENU
        self.menu = Menu(self, self.create_game, self.join_game)

        # OpenGL context
        pyglet.gl.glClearColor(0.5, 0.7, 1.0, 1.0)
        self.fog_color = (0.7, 0.8, 0.9)  # Light blue/grey fog color
        self.fog_density = 0.01 # Adjust as needed
        self.fog_start = config.FOG_START # Fog starts at this distance
        self.fog_end = config.FOG_END # Fog is fully opaque at this distance
        pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glFrontFace(pyglet.gl.GL_CCW)
        pyglet.gl.glDepthFunc(pyglet.gl.GL_LESS)

        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        pyglet.clock.schedule(self.update)
        self.set_exclusive_mouse(False)
        self.server = None
        self.client = None

        # Initialize shader program here
        self.program = self.create_shader_program() # Moved from start_game

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
        self.target_block_label = pyglet.text.Label(
            '',
            font_name='Arial',
            font_size=12,
            x=5, y=self.height - 65,
            anchor_x='left', anchor_y='top',
            batch=self.ui_batch
        )
        self.server_info_label = pyglet.text.Label(
            '',
            font_name='Arial',
            font_size=12,
            x=5, y=self.height - 85,
            anchor_x='left', anchor_y='top',
            batch=self.ui_batch
        )
        self.current_biome_info = {}

    def on_close(self):
        if self.server:
            self.server.stop()
        if self.client:
            self.client.close()
        super().on_close()

    def create_game(self, seed, port):
        print(f"Creating game with seed: {seed} and port: {port}")
        self.server = Server(port=int(port), seed=seed)
        self.server.start()
        # Connect a client to the newly created server for the host player
        self.client = Client('127.0.0.1', int(port), program=self.program)
        self.client.connect()
        self.start_game(seed)

    def join_game(self, seed, port, host):
        print(f"Joining game with host: {host}, port: {port} and seed: {seed}")
        self.client = Client(host, int(port))
        seed = self.client.connect()
        if seed:
            self.start_game(seed)

    def start_game(self, seed):
        if seed.isdigit():
            config.WORLD_SEED = int(seed)
        else:
            config.WORLD_SEED = hash(seed) & 0xFFFFFFFF

        self.game_state = GameState.GAME
        self.set_exclusive_mouse(True)

        # Initialisation du système fantôme
        self.player = Player((0, 2, 0))
        self.camera = GhostCamera(self)

        self.world = World(self.program, seed=config.WORLD_SEED)
        self.water = WaterPlane(size=500.0)  # Votre eau existante

        # Minimap
        self.show_minimap = False
        self.minimap = Minimap(self.world, self.world.textures, self.width, self.height)

        # HUD
        self.hud = HUD()

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
        self.target_block_label = pyglet.text.Label(
            '',
            font_name='Arial',
            font_size=12,
            x=5, y=self.height - 65,
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
        out vec3 world_pos; // Added for fog calculation

        uniform mat4 projection;
        uniform mat4 view;

        void main()
        {
            gl_Position = projection * view * vec4(position, 1.0);
            new_tex_coords = tex_coords;
            new_colors = colors;
            world_pos = position; // Pass world position to fragment shader
        }
        '''
        fragment_shader_source = '''
        #version 330 core
        in vec2 new_tex_coords;
        in vec3 new_colors;
        in vec3 world_pos; // Received from vertex shader

        out vec4 out_color;

        uniform sampler2D our_texture;
        uniform vec3 fog_color;   // Fog color
        uniform float fog_density; // Fog density (no longer used for linear fog, but kept for compatibility if needed)
        uniform float fog_start;   // Distance where fog starts
        uniform float fog_end;     // Distance where fog is fully opaque
        uniform mat4 view;         // View matrix to get camera position

        void main()
        {
            out_color = texture(our_texture, new_tex_coords);
            if(out_color.a < 0.1)
                discard;
            out_color *= vec4(new_colors, 1.0);

            // Fog calculation
            vec4 view_pos = view * vec4(world_pos, 1.0);
            float dist = length(view_pos.xyz); // Distance from camera to fragment

            // Linear fog
            float fog_factor = clamp((fog_end - dist) / (fog_end - fog_start), 0.0, 1.0);

            out_color = mix(vec4(fog_color, 1.0), out_color, fog_factor);
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
        if self.game_state == GameState.MENU:
            self.menu.on_resize(width, height)
        elif self.game_state == GameState.GAME:
            self.camera.on_resize(width, height)
            self.create_fbo_attachments(width, height) # Update FBO attachments on resize
            if hasattr(self, 'minimap'):
                self.minimap.window_width = width
                self.minimap.window_height = height
                # Re-calculate minimap size and position if needed, or let update_minimap handle it
                # For now, just updating width/height should be enough as minimap recalculates positions

    def on_mouse_motion(self, x, y, dx, dy):
        if self.game_state == GameState.GAME:
            # Sensibilité de la souris
            sensitivity = 0.15
            self.player.rotate(-dy * sensitivity, dx * sensitivity)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.game_state == GameState.MENU:
            self.menu.on_mouse_press(x, y, button, modifiers)
        elif self.game_state == GameState.GAME:
            if button == mouse.LEFT:
                if self.targeted_block_coords:
                    self.world.remove_block(self.targeted_block_coords)
            elif button == mouse.RIGHT:
                if self.block_placement_coords:
                    self.world.add_block(self.block_placement_coords, 'dirt')

    def on_text(self, text):
        if self.game_state == GameState.MENU:
            self.menu.on_text(text)

    def update(self, dt):
        if self.server:
            self.server_info_label.text = f"Server: {self.server.get_client_count()} players connected"
        else:
            self.server_info_label.text = ""

        if self.game_state == GameState.GAME:
            self.total_time += dt # Update total time
            self.player.update(dt, self.keys, self.world)
            self.camera.update(self.player)

            # Send and receive player data if connected to a server
            if self.client:
                self.client.send_player_data(self.player.position, (self.player.pitch, self.player.yaw))
                self.client.receive_player_data()

            # Mettre à jour l'affichage de position
            pos = self.player.position
            self.info_label.text = f'Position: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) | Pitch: {self.player.pitch:.1f}° | Yaw: {self.player.yaw:.1f}°'
            mode_text = f"Mode: {'Ghost' if self.player.ghost_mode else 'Grounded'}"
            if self.player.is_swimming:
                mode_text += " (Swimming)"
            self.mode_label.text = mode_text

            # Get current biome info
            self.current_biome_info = self.world.get_biome(pos[0], pos[2])
            biome_name = self.current_biome_info.get('name', 'N/A')
            self.debug_label.text = f"Debug Info: {self.player.debug_info} | Biome: {biome_name.capitalize()}"

            # Raycast to find targeted block
            player_pos = self.player.position
            eye_pos = (player_pos[0], player_pos[1] + EYE_HEIGHT, player_pos[2])

            pitch_rad = math.radians(self.player.pitch)
            yaw_rad = math.radians(self.player.yaw)

            dx = math.sin(yaw_rad) * math.cos(pitch_rad)
            dy = -math.sin(pitch_rad)
            dz = -math.cos(yaw_rad) * math.cos(pitch_rad)
            looking_vector = (dx, dy, dz)

            self.targeted_block_coords, self.targeted_block_type, self.block_placement_coords = self._raycast(eye_pos, looking_vector)

            if self.targeted_block_type:
                self.target_block_label.text = f"Target Block: {self.targeted_block_type.capitalize()} at {self.targeted_block_coords}"
            else:
                self.target_block_label.text = "Target Block: None"

            # Mettre à jour votre monde si vous l'avez
            self.world.update(dt, self.player.position)

    def on_draw(self):
        self.clear()
        if self.game_state == GameState.MENU:
            pyglet.gl.glDisable(pyglet.gl.GL_DEPTH_TEST)
            pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE)
            self.menu.draw()
        elif self.game_state == GameState.GAME:
            pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)
            pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
            # Render to FBO
            pyglet.gl.glBindFramebuffer(pyglet.gl.GL_FRAMEBUFFER, self.fbo)
            self.clear() # Clear FBO

            # Rendu 3D
            self.program.use()
            self.program['projection'] = self.camera.projection
            self.program['view'] = self.camera.view
            self.program['fog_color'] = self.fog_color
            self.program['fog_start'] = self.fog_start
            self.program['fog_end'] = self.fog_end

            self.world.draw(self.player.position)

            # Draw other players
            if self.client:
                self.client.draw_other_players(self.camera.view) # Pass view_matrix

            self.program.stop()

            # Dessiner votre eau si vous l'avez
            self.water.draw(self.camera.projection, self.camera.view, self.total_time, self.player.position,
                            self.fog_color, self.fog_start, self.fog_end)

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
            # Ensure blending is enabled for UI elements
            pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
            pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
            pyglet.gl.glDisable(pyglet.gl.GL_DEPTH_TEST) # Disable depth test for 2D UI

            temp = self.current_biome_info.get('temp', 0)
            humid = self.current_biome_info.get('humid', 0)
            self.hud.draw(self.width, self.height, temp, humid)
            self.ui_batch.draw()

            if self.show_minimap:
                self.minimap.update_minimap(self.player.position)
                self.minimap.draw()

            # Restore depth test for 3D rendering (if it was enabled before)
            pyglet.gl.glEnable(pyglet.gl.GL_DEPTH_TEST)

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
        if self.game_state == GameState.MENU:
            self.menu.on_key_press(symbol, modifiers)
        elif self.game_state == GameState.GAME:
            if symbol == key.ESCAPE:
                self.game_state = GameState.MENU
                self.set_exclusive_mouse(False)
                if self.server:
                    self.server.stop()
                    self.server = None
                if self.client:
                    self.client.close()
                    self.client = None
            elif symbol == key.T:
                self.player.toggle_ghost_mode()
            elif symbol == key.M:
                self.show_minimap = not self.show_minimap

    def _raycast(self, position, vector, max_distance=10):
        """
        Performs a raycast from a position in a given direction to find the first block hit.
        Returns (block_x, block_y, block_z), block_type, and the previous position (prior_x, prior_y, prior_z).
        """
        x, y, z = position
        dx, dy, dz = vector

        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        step_z = 1 if dz > 0 else -1

        t_max_x = (math.floor(x) + step_x - x) / dx if dx != 0 else float('inf')
        t_max_y = (math.floor(y) + step_y - y) / dy if dy != 0 else float('inf')
        t_max_z = (math.floor(z) + step_z - z) / dz if dz != 0 else float('inf')

        t_delta_x = abs(1 / dx) if dx != 0 else float('inf')
        t_delta_y = abs(1 / dy) if dy != 0 else float('inf')
        t_delta_z = abs(1 / dz) if dz != 0 else float('inf')

        current_x, current_y, current_z = int(math.floor(x)), int(math.floor(y)), int(math.floor(z))
        prior_x, prior_y, prior_z = current_x, current_y, current_z
        distance = 0.0

        while distance < max_distance:
            block_type = self.world.blocks.get((current_x, current_y, current_z))
            if block_type is not None:
                return (current_x, current_y, current_z), block_type, (prior_x, prior_y, prior_z)

            prior_x, prior_y, prior_z = current_x, current_y, current_z
            if t_max_x < t_max_y and t_max_x < t_max_z:
                current_x += step_x
                distance = t_max_x
                t_max_x += t_delta_x
            elif t_max_y < t_max_z:
                current_y += step_y
                distance = t_max_y
                t_max_y += t_delta_y
            else:
                current_z += step_z
                distance = t_max_z
                t_max_z += t_delta_z
        return None, None, None

    def run(self):
        pyglet.app.run()
