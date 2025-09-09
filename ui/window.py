import math
import pyglet
from pyglet.graphics import shader
from pyglet.window import key
from pyglet.math import Mat4, Vec3

from core.world import World
from core.player import Player
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
        pos = Vec3(player.position[0], player.position[1], player.position[2])
        
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
        self.world = World(self.program)  # Votre monde existant
        self.water = WaterPlane(size=2000.0)  # Votre eau existante
        
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        pyglet.clock.schedule(self.update)
        self.set_exclusive_mouse(True)

        # UI
        self.ui_batch = pyglet.graphics.Batch()
        self.info_label = pyglet.text.Label(
            f'Position: {self.player.position}',
            font_name='Arial',
            font_size=12,
            x=5, y=self.height - 20,
            anchor_x='left', anchor_y='top',
            batch=self.ui_batch
        )

    def create_shader_program(self):
        # Votre code de shader existant
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

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.camera.on_resize(width, height)

    def on_mouse_motion(self, x, y, dx, dy):
        # Sensibilité de la souris
        sensitivity = 0.15
        self.player.rotate(-dy * sensitivity, dx * sensitivity)

    def update(self, dt):
        self.player.update(dt, self.keys)
        self.camera.update(self.player)
        
        # Mettre à jour l'affichage de position
        pos = self.player.position
        self.info_label.text = f'Position: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) | Pitch: {self.player.pitch:.1f}° | Yaw: {self.player.yaw:.1f}°'
        
        # Mettre à jour votre monde si vous l'avez
        self.world.update(self.player.position)

    def on_draw(self):
        self.clear()
        
        # Rendu 3D
        self.program.use()
        self.program['projection'] = self.camera.projection
        self.program['view'] = self.camera.view
        
        # Dessiner votre monde ici
        self.world.draw(self.player.position)
        
        self.program.stop()
        
        # Dessiner votre eau si vous l'avez
        self.water.draw(self.camera.projection, self.camera.view)
        
        # UI
        self.ui_batch.draw()

    def draw_underwater_filter(self):
        # Create a semi-transparent blue rectangle that covers the entire window
        underwater_rect = pyglet.shapes.Rectangle(0, 0, self.width, self.height, color=(0, 76, 153, 128)) # RGBA (0-255)
        underwater_rect.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            pyglet.app.exit()

    def run(self):
        pyglet.app.run()