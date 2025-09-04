import math
import pyglet
import noise
from pyglet.gl import *
from pyglet.window import key
import threading
import queue

CHUNK_SIZE = 16
RENDER_DISTANCE = 2
BLOCK_HEIGHT = 20
WORLD_SEED = 88

import time
import ctypes
from pyglet.gl import *

class WaterPlane:
    def __init__(self, height=0.0, size=200.0):
        self.height = height
        self.size = size

        # Créer un quad simple
        s = self.size / 2
        h = self.height
        self.vertices = [
            -s, h, -s,  # coin bas-gauche
            -s, h,  s,  # coin haut-gauche
             s, h,  s,  # coin haut-droite
             s, h, -s   # coin bas-droite
        ]

        # Vertex shader (simple)
        vertex_src = """
        #version 120
        attribute vec3 position;
        varying vec2 v_uv;
        void main() {
            v_uv = position.xz * 0.05;
            gl_Position = gl_ModelViewProjectionMatrix * vec4(position, 1.0);
        }
        """

        # Fragment shader (scintillement pour effet vivant)
        fragment_src = """
        #version 120
        uniform float u_time;
        varying vec2 v_uv;
        void main() {
            float flicker = 0.5 + 0.5 * sin(u_time*3.0 + gl_FragCoord.x*0.05 + gl_FragCoord.y*0.05);
            vec3 color = vec3(0.2, 0.4, 0.8) * flicker;
            gl_FragColor = vec4(color, 0.8);
        }
        """

        # Compiler shader
        self.program = self.create_shader(vertex_src, fragment_src)
        self.time_loc = glGetUniformLocation(self.program, b"u_time")

    def create_shader(self, vs_source, fs_source):
        def compile_shader(src, shader_type):
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
        glUniform1f(self.time_loc, t)  # Mise à jour du temps pour scintillement

        # Désactiver le face culling pour voir le quad des deux côtés
        glDisable(GL_CULL_FACE)

        glBegin(GL_QUADS)
        glVertex3f(self.vertices[0], self.vertices[1], self.vertices[2])
        glVertex3f(self.vertices[3], self.vertices[4], self.vertices[5])
        glVertex3f(self.vertices[6], self.vertices[7], self.vertices[8])
        glVertex3f(self.vertices[9], self.vertices[10], self.vertices[11])
        glEnd()

        # Restaurer le culling si nécessaire
        glEnable(GL_CULL_FACE)

        glUseProgram(0)
        glDisable(GL_BLEND)

class World:
    def __init__(self):
        self.blocks = {}  # Pour collisions
        self.chunks = {}  # {(cx, cz): {'blocks': dict, 'pending': list}}
        self.chunk_batches = {}  # {(cx, cz): (block_batch, edge_batch)}
        self.chunks_to_update = []  # Liste des chunks en cours d'apparition progressive
        self.chunk_queue = queue.Queue()  # Chunks générés par les threads
        self.textures = Textures()

    def update(self, player_pos):
        chunk_x = int(player_pos[0] // CHUNK_SIZE)
        chunk_z = int(player_pos[2] // CHUNK_SIZE)

        # Générer les chunks manquants
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE+1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE+1):
                cx, cz = chunk_x + dx, chunk_z + dz
                if (cx, cz) not in self.chunks:
                    threading.Thread(target=self.generate_chunk_thread, args=(cx, cz), daemon=True).start()

        # Récupérer les chunks générés
        while not self.chunk_queue.empty():
            cx, cz, chunk_blocks = self.chunk_queue.get()
            pending = list(chunk_blocks.items())  # Liste des blocs à ajouter progressivement
            self.chunks[(cx, cz)] = {'blocks': chunk_blocks, 'pending': pending}
            self.chunks_to_update.append((cx, cz))
            # Créer le batch vide pour ce chunk
            self.chunk_batches[(cx, cz)] = (pyglet.graphics.Batch(), pyglet.graphics.Batch())

        # Ajouter progressivement les blocs par frame
        blocks_per_frame = 100
        chunks_done = []
        for cx, cz in self.chunks_to_update[:]:  # copier la liste pour éviter modification en boucle
            if (cx, cz) not in self.chunks:
                chunks_done.append((cx, cz))
                continue

            chunk_data = self.chunks[(cx, cz)]
            pending = chunk_data['pending']
            block_batch, edge_batch = self.chunk_batches[(cx, cz)]

            for _ in range(min(blocks_per_frame, len(pending))):
                pos, block_type = pending.pop(0)
                self.add_block_to_batch(pos, block_type, block_batch, edge_batch)
                self.blocks[pos] = block_type

            if not pending:
                chunks_done.append((cx, cz))

        # Retirer les chunks terminés ou supprimés
        for chunk in chunks_done:
            if chunk in self.chunks_to_update:
                self.chunks_to_update.remove(chunk)

        # Supprimer les chunks trop loin
        self.cleanup_chunks(player_pos)

    def generate_chunk_thread(self, cx, cz):
        chunk_blocks = {}
        for x in range(cx*CHUNK_SIZE, (cx+1)*CHUNK_SIZE):
            for z in range(cz*CHUNK_SIZE, (cz+1)*CHUNK_SIZE):
                h = self.get_height(x, z)
                for y in range(-BLOCK_HEIGHT, h+1):
                    if y <= 0:
                        block_type = "water"
                    elif y < h - 1:
                        block_type = "stone" if h > 12 else "dirt"
                    else:
                        block_type = "snow" if h > 12 else "stone" if h > 8 else "grass" if h > 4 else "dirt" if h > 2 else "water"
                    chunk_blocks[(x, y, z)] = block_type
        self.chunk_queue.put((cx, cz, chunk_blocks))

    def get_height(self, x, z):
        base = noise.pnoise2(x * 0.01, z * 0.01, octaves=3, base=WORLD_SEED) * 50
        detail = noise.pnoise2(x * 0.1, z * 0.1, octaves=2, base=WORLD_SEED) * 5
        return int(base + detail - 5) + 10

    def add_block_to_batch(self, pos, block_type, block_batch, edge_batch):
        x, y, z = pos
        texture = self.textures.get(block_type)
        if texture is None:
            return

        faces = [
            ((0,0,1), [(x-0.5,y-0.5,z+0.5),(x+0.5,y-0.5,z+0.5),(x+0.5,y+0.5,z+0.5),(x-0.5,y+0.5,z+0.5)]),
            ((0,0,-1), [(x+0.5,y-0.5,z-0.5),(x-0.5,y-0.5,z-0.5),(x-0.5,y+0.5,z-0.5),(x+0.5,y+0.5,z-0.5)]),
            ((-1,0,0), [(x-0.5,y-0.5,z+0.5),(x-0.5,y+0.5,z+0.5),(x-0.5,y+0.5,z-0.5),(x-0.5,y-0.5,z-0.5)]),
            ((1,0,0), [(x+0.5,y-0.5,z-0.5),(x+0.5,y+0.5,z-0.5),(x+0.5,y+0.5,z+0.5),(x+0.5,y-0.5,z+0.5)]),
            ((0,1,0), [(x-0.5,y+0.5,z-0.5),(x-0.5,y+0.5,z+0.5),(x+0.5,y+0.5,z+0.5),(x+0.5,y+0.5,z-0.5)]),
            ((0,-1,0), [(x-0.5,y-0.5,z+0.5),(x-0.5,y-0.5,z-0.5),(x+0.5,y-0.5,z-0.5),(x+0.5,y-0.5,z+0.5)]),
        ]

        uv_coords = [0,0, 1,0, 1,1, 1,1, 0,1, 0,0]

        for direction, verts in faces:
            neighbor = (x + direction[0], y + direction[1], z + direction[2])
            if neighbor not in self.blocks:
                tri_verts = [*verts[0],*verts[1],*verts[2], *verts[2],*verts[3],*verts[0]]
                block_batch.add(6, GL_TRIANGLES, pyglet.graphics.TextureGroup(texture),
                                ('v3f', tri_verts),
                                ('t2f', uv_coords))

                edge_batch.add(8, GL_LINES, None,
                               ('v3f', (*verts[0],*verts[1],*verts[1],*verts[2],
                                        *verts[2],*verts[3],*verts[3],*verts[0])),
                               ('c3f', (0.0,0.0,0.0)*8))

    def cleanup_chunks(self, player_pos):
        to_delete = []
        for (cx, cz) in self.chunks:
            dx = (cx*CHUNK_SIZE + CHUNK_SIZE/2) - player_pos[0]
            dz = (cz*CHUNK_SIZE + CHUNK_SIZE/2) - player_pos[2]
            max_dist = CHUNK_SIZE * (RENDER_DISTANCE + 1)
            if dx*dx + dz*dz > max_dist*max_dist:
                to_delete.append((cx, cz))

        for key in to_delete:
            chunk_blocks = self.chunks.pop(key, {}).get('blocks', {})
            for pos in chunk_blocks:
                self.blocks.pop(pos, None)
            self.chunk_batches.pop(key, None)
            if key in self.chunks_to_update:
                self.chunks_to_update.remove(key)

    def draw(self, player_pos):
        max_render_sq = (CHUNK_SIZE * RENDER_DISTANCE) ** 2
        for (cx, cz), (block_batch, edge_batch) in self.chunk_batches.items():
            chunk_center_x = (cx + 0.5) * CHUNK_SIZE
            chunk_center_z = (cz + 0.5) * CHUNK_SIZE
            dx = chunk_center_x - player_pos[0]
            dz = chunk_center_z - player_pos[2]
            if dx*dx + dz*dz > max_render_sq:
                continue
            block_batch.draw()
            glLineWidth(1.5)
            edge_batch.draw()

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
            return

        # Gravité
        self.velocity[1] += self.gravity * dt

        # Saut
        if keys[key.SPACE] and self.on_ground:
            self.velocity[1] = self.jump_speed
            self.on_ground = False

        # Vérifier si dans l'eau
        in_water = self.position[1] < 0


        # Appliquer flottabilité et résistance si dans l'eau
        if in_water:
            self.velocity[1] += 10.0 * dt    # poussée vers le haut
            self.velocity[1] *= 0.5          # résistance verticale
            speed_multiplier = 0.5           # résistance horizontale
            # Monter avec SPACE
            if keys[key.SPACE]:
                self.velocity[1] += self.jump_speed  # ajuste la vitesse verticale selon le feeling
        else:
            speed_multiplier = 1.0

        # Déplacement horizontal
        self.move_with_collision(dx*speed_multiplier, 0, dz*speed_multiplier, world)
        # Déplacement vertical
        self.move_with_collision(0, self.velocity[1]*dt, 0, world)


    def move_with_collision(self, dx, dy, dz, world):
        import math

        half_width = 0.45
        height = 0.95

        # Déplacement sur X
        new_x = self.position[0] + dx
        blocked = False
        for x in range(math.floor(new_x - half_width), math.ceil(new_x + half_width)):
            for y in range(math.floor(self.position[1]), math.ceil(self.position[1] + height)):
                for z in range(math.floor(self.position[2] - half_width), math.ceil(self.position[2] + half_width)):
                    if (x, y, z) in world.blocks:
                        blocked = True
        if not blocked:
            self.position[0] = new_x

        # Déplacement sur Z
        new_z = self.position[2] + dz
        blocked = False
        for x in range(math.floor(self.position[0] - half_width), math.ceil(self.position[0] + half_width)):
            for y in range(math.floor(self.position[1]), math.ceil(self.position[1] + height)):
                for z in range(math.floor(new_z - half_width), math.ceil(new_z + half_width)):
                    if (x, y, z) in world.blocks:
                        blocked = True
        if not blocked:
            self.position[2] = new_z

        # Déplacement sur Y (gravité et collisions)
        new_y = self.position[1] + dy
        self.on_ground = False
        y_start = math.floor(new_y - 0.01)
        y_end = math.ceil(new_y + height + 0.01)

        for x in range(math.floor(self.position[0] - half_width), math.ceil(self.position[0] + half_width)):
            for y in range(y_start, y_end):
                for z in range(math.floor(self.position[2] - half_width), math.ceil(self.position[2] + half_width)):
                    block = world.blocks.get((x, y, z))
                    if block:
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
        self.water = WaterPlane(size=2000.0)

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
        self.world.draw(self.player.position)
        self.water.draw()
        # Filtre bleu sous-marin
        if self.player.position[1] < 0:  # sous l'eau
            self.draw_underwater_filter()
        else:
            glColor4f(1.0, 1.0, 1.0, 1.0)
        glPopMatrix()

    def draw_underwater_filter(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)  # Pour que le quad soit toujours visible

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glColor4f(0.0, 0.3, 0.6, 0.25)  # Bleu semi-transparent
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(self.width, 0)
        glVertex2f(self.width, self.height)
        glVertex2f(0, self.height)
        glEnd()

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)

    
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
