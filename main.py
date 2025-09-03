import math
import pyglet
import noise
from pyglet.gl import *
from pyglet.window import key
import threading
import queue

CHUNK_SIZE = 16
RENDER_DISTANCE = 3
BLOCK_HEIGHT = 20
import time
import ctypes
from pyglet.gl import *

class WaterPlane:
    def __init__(self, height=0.0, size=1000.0):
        self.height = height
        self.size = size

        # Vertex shader
        vertex_src = """
        #version 120
        attribute vec3 position;
        varying vec2 v_uv;
        void main() {
            v_uv = position.xz * 0.05;
            gl_Position = gl_ModelViewProjectionMatrix * vec4(position, 1.0);
        }
        """

        # Fragment shader
        fragment_src = """
        #version 120
        uniform float u_time;
        varying vec2 v_uv;

        float rand(vec2 co){
            return fract(sin(dot(co.xy, vec2(12.9898,78.233))) * 43758.5453);
        }

        void main() {
            float wave = sin(v_uv.x*10.0 + u_time*2.0)*0.05
                    + cos(v_uv.y*12.0 + u_time*1.5)*0.05;
            float noise = (rand(v_uv*10.0 + u_time) - 0.5) * 0.02;

            float brightness = 0.6 + 0.2*sin(u_time*0.5 + v_uv.x*5.0);
            vec3 color = vec3(0.2, 0.4, 0.8) * brightness;

            float sparkle = smoothstep(0.02, 0.04, abs(sin(u_time*5.0 + v_uv.x*10.0)));
            color += vec3(sparkle*0.2);

            gl_FragColor = vec4(color, 0.5 + wave*0.2 + noise*0.3);
        }
        """

        # Compiler le shader
        self.program = self.create_shader(vertex_src, fragment_src)
        self.time_loc = glGetUniformLocation(self.program, b"u_time")

        # Quad géant
        s = self.size
        h = self.height
        self.vertices = [
            -s, h, -s,  # coin bas-gauche
            -s, h,  s,  # coin haut-gauche
             s, h,  s,  # coin haut-droite
             s, h, -s   # coin bas-droite
        ]

    def create_shader(self, vs_source: bytes, fs_source: bytes):
        def compile_shader(src: bytes, shader_type):
            shader = glCreateShader(shader_type)
            src_buffer = ctypes.create_string_buffer(src.encode('utf-8'))
            src_ptr = ctypes.cast(ctypes.pointer(src_buffer), ctypes.POINTER(ctypes.c_char))
            src_pp = ctypes.pointer(ctypes.cast(src_ptr, ctypes.POINTER(ctypes.c_char)))
            length = ctypes.c_int(len(src))
            glShaderSource(shader, 1, src_pp, ctypes.byref(length))
            glCompileShader(shader)

            status = ctypes.c_int()
            glGetShaderiv(shader, GL_COMPILE_STATUS, ctypes.byref(status))
            if not status.value:
                log_length = ctypes.c_int()
                glGetShaderiv(shader, GL_INFO_LOG_LENGTH, ctypes.byref(log_length))
                log = ctypes.create_string_buffer(log_length.value)
                glGetShaderInfoLog(shader, log_length, None, log)
                raise RuntimeError("Shader compile error: " + log.value.decode(errors="ignore"))
            return shader

        vs = compile_shader(vs_source, GL_VERTEX_SHADER)
        fs = compile_shader(fs_source, GL_FRAGMENT_SHADER)

        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        status = ctypes.c_int()
        glGetProgramiv(program, GL_LINK_STATUS, ctypes.byref(status))
        if not status.value:
            log_length = ctypes.c_int()
            glGetProgramiv(program, GL_INFO_LOG_LENGTH, ctypes.byref(log_length))
            log = ctypes.create_string_buffer(log_length.value)
            glGetProgramInfoLog(program, log_length, None, log)
            raise RuntimeError("Shader link error: " + log.value.decode(errors="ignore"))

        return program

    def draw(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glUseProgram(self.program)
        t = time.time()
        glUniform1f(self.time_loc, t)

        glBegin(GL_QUADS)
        glVertex3f(self.vertices[0], self.vertices[1], self.vertices[2])
        glVertex3f(self.vertices[3], self.vertices[4], self.vertices[5])
        glVertex3f(self.vertices[6], self.vertices[7], self.vertices[8])
        glVertex3f(self.vertices[9], self.vertices[10], self.vertices[11])
        glEnd()

        glUseProgram(0)
        glDisable(GL_BLEND)


class World:
    def __init__(self):
        self.chunks = {}
        self.blocks = {}
        self.batch = pyglet.graphics.Batch()
        self.edge_batch = pyglet.graphics.Batch()
        self.chunk_queue = queue.Queue()  # Chunks générés par les threads
        self.pending_blocks = []         # Blocs à ajouter progressivement
        self.textures = Textures()

    def update(self, player_pos):
        chunk_x = int(player_pos[0] // CHUNK_SIZE)
        chunk_z = int(player_pos[2] // CHUNK_SIZE)

        # Générer les chunks manquants dans un thread
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE+1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE+1):
                cx, cz = chunk_x + dx, chunk_z + dz
                if (cx, cz) not in self.chunks:
                    threading.Thread(target=self.generate_chunk_thread, args=(cx, cz), daemon=True).start()

        # Récupérer les chunks générés par les threads
        while not self.chunk_queue.empty():
            cx, cz, chunk_blocks = self.chunk_queue.get()
            self.chunks[(cx, cz)] = chunk_blocks
            self.pending_blocks.extend(chunk_blocks.items())

        # Ajouter progressivement quelques blocs par frame pour éviter le freeze
        blocks_per_frame = 800
        for _ in range(min(blocks_per_frame, len(self.pending_blocks))):
            pos, block_type = self.pending_blocks.pop(0)
            self.add_block(pos, block_type)

    def generate_chunk_thread(self, cx, cz):
        """Génère les données d'un chunk dans un thread séparé."""
        chunk_blocks = {}
        for x in range(cx*CHUNK_SIZE, (cx+1)*CHUNK_SIZE):
            for z in range(cz*CHUNK_SIZE, (cz+1)*CHUNK_SIZE):
                h = self.get_height(x, z)
                for y in range(-BLOCK_HEIGHT, h+1):
                    if y < 0: block_type = "water"
                    elif y == 0: block_type = "dirt"
                    elif y < h - 1: block_type = "stone" if h > 12 else "dirt"
                    else: block_type = "snow" if h > 6 else "stone" if h > 3 else "grass"
                    chunk_blocks[(x, y, z)] = block_type
        self.chunk_queue.put((cx, cz, chunk_blocks))

    def get_height(self, x, z):
        base = noise.pnoise2(x * 0.01, z * 0.01, octaves=3) * 50
        detail = noise.pnoise2(x * 0.1, z * 0.1, octaves=2) * 5
        return int(base + detail - 5) + 10

    def add_block(self, position, block_type):
        x, y, z = position
        self.blocks[position] = block_type

        # # Couleurs selon le type de bloc
        # if block_type == "grass": color = (0.0, 0.5, 0.0) * 6
        # elif block_type == "dirt": color = (0.5, 0.25, 0.0) * 6
        # elif block_type == "water": color = (0.0, 0.0, 1.0) * 6
        # elif block_type == "stone": color = (0.5, 0.5, 0.5) * 6
        # elif block_type == "snow": color = (1.0, 1.0, 1.0) * 6
        # else: color = (1.0, 0.0, 1.0) * 6

        texture = self.textures.get(block_type)
        if texture is None:
            return

        # Définir les faces
        faces = [
            ((0,0,1), [(x-0.5,y-0.5,z+0.5), (x+0.5,y-0.5,z+0.5), (x+0.5,y+0.5,z+0.5), (x-0.5,y+0.5,z+0.5)]),
            ((0,0,-1), [(x+0.5,y-0.5,z-0.5), (x-0.5,y-0.5,z-0.5), (x-0.5,y+0.5,z-0.5), (x+0.5,y+0.5,z-0.5)]),
            ((-1,0,0), [(x-0.5,y-0.5,z+0.5),(x-0.5,y+0.5,z+0.5),(x-0.5,y+0.5,z-0.5),(x-0.5,y-0.5,z-0.5)]),
            ((1,0,0), [(x+0.5,y-0.5,z-0.5),(x+0.5,y+0.5,z-0.5),(x+0.5,y+0.5,z+0.5),(x+0.5,y-0.5,z+0.5)]),
            ((0,1,0), [(x-0.5,y+0.5,z-0.5),(x-0.5,y+0.5,z+0.5),(x+0.5,y+0.5,z+0.5),(x+0.5,y+0.5,z-0.5)]),
            ((0,-1,0), [(x-0.5,y-0.5,z+0.5),(x-0.5,y-0.5,z-0.5),(x+0.5,y-0.5,z-0.5),(x+0.5,y-0.5,z+0.5)]),
        ]

        uv_coords = [
            0,0, 1,0, 1,1,  # triangle 1
            1,1, 0,1, 0,0   # triangle 2
        ]

        for direction, verts in faces:
            neighbor = (x + direction[0], y + direction[1], z + direction[2])
            if neighbor not in self.blocks:
                # 2 triangles par face
                tri_verts = [*verts[0], *verts[1], *verts[2], *verts[2], *verts[3], *verts[0]]
                self.batch.add(6, GL_TRIANGLES, pyglet.graphics.TextureGroup(texture),
                            ('v3f', tri_verts),
                            ('t2f', uv_coords))

                # Arêtes (pas besoin de changer)
                self.edge_batch.add(8, GL_LINES, None,
                                    ('v3f', (*verts[0],*verts[1],*verts[1],*verts[2],
                                            *verts[2],*verts[3],*verts[3],*verts[0])),
                                    ('c3f', (0.0,0.0,0.0)*8))

    def draw(self):
        self.batch.draw()
        glLineWidth(1.5)
        self.edge_batch.draw()

class Player:
    def __init__(self, position=(0,2,0), rotation=(0,0)):
        self.position = list(position)
        self.rotation = list(rotation)
        self.velocity = [0, 0, 0]  # vx, vy, vz
        self.on_ground = False
        self.gravity = -20.0
        self.jump_speed = 8.0
        self.fly_mode = True

    def update(self, dt, keys, world):
        speed = dt * 5
        yaw = math.radians(-self.rotation[1])
        forward = (math.sin(yaw), 0, math.cos(yaw))
        right = (math.cos(yaw), 0, -math.sin(yaw))

        dx = dz = 0
        if keys[key.UP] or keys[key.W]: dx += forward[0]*speed; dz += forward[2]*speed
        if keys[key.DOWN] or keys[key.S]: dx -= forward[0]*speed; dz -= forward[2]*speed
        if keys[key.LEFT] or keys[key.A]: dx += right[0]*speed; dz += right[2]*speed
        if keys[key.RIGHT] or keys[key.D]: dx -= right[0]*speed; dz -= right[2]*speed

        if self.fly_mode:
            dy = 0
            if keys[key.SPACE]: dy += speed
            if keys[key.LSHIFT]: dy -= speed
            self.position[0] += dx
            self.position[1] += dy
            self.position[2] += dz
        else:
            # Gravité
            self.velocity[1] += self.gravity * dt

            # Saut
            if keys[key.SPACE] and self.on_ground:
                self.velocity[1] = self.jump_speed
                self.on_ground = False

            # Déplacement horizontal et collision
            self.move_with_collision(dx, 0, dz, world)

            # Déplacement vertical et collision
            self.move_with_collision(0, self.velocity[1]*dt, 0, world)

    def move_with_collision(self, dx, dy, dz, world):
        half_width = 0.45
        height = 0.95

        # Déplacement sur X
        new_x = self.position[0] + dx
        blocked = False
        for x in range(int(new_x - half_width), int(new_x + half_width) + 1):
            for y in range(int(self.position[1]), int(self.position[1] + height) + 1):
                for z in range(int(self.position[2] - half_width), int(self.position[2] + half_width) + 1):
                    if (x, y, z) in world.blocks:
                        blocked = True
        if not blocked:
            self.position[0] = new_x

        # Déplacement sur Z
        new_z = self.position[2] + dz
        blocked = False
        for x in range(int(self.position[0] - half_width), int(self.position[0] + half_width) + 1):
            for y in range(int(self.position[1]), int(self.position[1] + height) + 1):
                for z in range(int(new_z - half_width), int(new_z + half_width) + 1):
                    if (x, y, z) in world.blocks:
                        blocked = True
        if not blocked:
            self.position[2] = new_z

        # Déplacement sur Y (gravité et saut)
        new_y = self.position[1] + dy
        self.on_ground = False
        for x in range(int(self.position[0] - half_width), int(self.position[0] + half_width) + 1):
            for y in range(int(new_y), int(new_y + height) + 1):
                for z in range(int(self.position[2] - half_width), int(self.position[2] + half_width) + 1):
                    if (x, y, z) in world.blocks:
                        if dy > 0:
                            new_y = y - height
                            self.velocity[1] = 0
                        elif dy < 0:
                            new_y = y + 1
                            self.velocity[1] = 0
                            self.on_ground = True
        self.position[1] = new_y


    def toggle_fly(self):
        self.fly_mode = not self.fly_mode


class Window(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_minimum_size(300, 200)
        self.world = World()
        self.player = Player((0,1,0), (-30,0))
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        pyglet.clock.schedule(self.update)
        self.set_exclusive_mouse(True)
        self.water = WaterPlane(height=0.0, size=2000.0)

    def on_resize(self, width, height):
        fb_w, fb_h = self.get_framebuffer_size()
        glViewport(0, 0, fb_w, max(1, fb_h))
        return super().on_resize(width, height)

    def on_mouse_motion(self, x, y, dx, dy):
        self.player.rotation[0] -= dy / 8
        self.player.rotation[1] += dx / 8
        self.player.rotation[0] = max(-90, min(90, self.player.rotation[0]))

    def update(self, dt):
        self.player.update(dt, self.keys, self.world)
        self.world.update(self.player.position)

    def on_draw(self):
        self.clear()
        fb_w, fb_h = self.get_framebuffer_size()
        aspect = fb_w / max(1, fb_h)
        glViewport(0, 0, fb_w, fb_h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(65.0, aspect, 0.1, 4000.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glPushMatrix()
        rotY = math.radians(-self.player.rotation[1])
        rotX = math.radians(self.player.rotation[0])
        look_x = math.sin(rotY)*math.cos(rotX)
        look_y = -math.sin(rotX)
        look_z = math.cos(rotY)*math.cos(rotX)
        eye = (self.player.position[0], self.player.position[1] + 0.5, self.player.position[2])
        center = (eye[0]+look_x, eye[1]+look_y, eye[2]+look_z)
        gluLookAt(eye[0], eye[1], eye[2], center[0], center[1], center[2], 0,1,0)
        self.world.draw()
        self.water.draw()
        glPopMatrix()
    
    def on_key_press(self, symbol, modifiers):
        if symbol == key.T:
            self.player.toggle_fly()
        elif symbol == key.ESCAPE:
            self.close() 

    def run(self):
        pyglet.app.run()

class Textures:
    def __init__(self):
        self.textures = {}
        self.load_textures()

    def load_textures(self):
        self.textures['grass'] = pyglet.image.load('grass.png').get_texture()
        self.textures['dirt'] = pyglet.image.load('dirt.png').get_texture()
        self.textures['stone'] = pyglet.image.load('stone.png').get_texture()
        self.textures['snow'] = pyglet.image.load('snow.png').get_texture()
        self.textures['water'] = pyglet.image.load('water.png').get_texture()

    def get(self, block_type):
        return self.textures.get(block_type)

if __name__ == '__main__':
    config = pyglet.gl.Config(double_buffer=True, depth_size=24, sample_buffers=1, samples=4)
    window = Window(config=config, width=800, height=600, caption='pyCraft Infinite', resizable=True)
    glClearColor(0.5, 0.7, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glFrontFace(GL_CCW)
    glDepthFunc(GL_LESS)
    window.run()
