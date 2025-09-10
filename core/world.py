import threading, queue, math
import pyglet
import noise
from core.textures import Textures
from core.vegetation import Vegetation
from core.sprites import Sprites
from core.animals import Animals # Importer la nouvelle classe
from config import CHUNK_SIZE, RENDER_DISTANCE, WORLD_SEED, SPRITE_RENDER_DISTANCE

class World:
    def __init__(self, program):
        self.program = program
        self.blocks = {}
        self.chunks = {}
        self.chunk_batches = {}
        
        self.chunk_generation_queue = queue.Queue()
        self.chunk_meshing_queue = queue.Queue()

        self.textures = Textures()
        self.vegetation = Vegetation(seed=WORLD_SEED)
        
        # Système de sprites (basé sur les chunks)
        self.sprites = Sprites(seed=WORLD_SEED)
        self.sprite_chunks = {}
        self.sprite_meshing_queue = queue.Queue()
        self.sprite_batches = {}
        self.sprite_generation_queue = queue.Queue()

        # Système d'animaux (basé sur des entités)
        self.animals = Animals(seed=WORLD_SEED + 1)
        self.animals.set_textures(self.textures)
        self.animal_batches = {} # Un seul dictionnaire de batches, non lié aux chunks

        # Démarrer les workers pour le terrain et les sprites
        threading.Thread(target=self.chunk_generation_worker, daemon=True).start()
        threading.Thread(target=self.sprite_generation_worker, daemon=True).start()

    def chunk_generation_worker(self):
        while True:
            cx, cz, player_chunk_x, player_chunk_z = self.chunk_generation_queue.get()
            if (cx, cz) in self.chunks and self.chunks[(cx, cz)].get('status') != 'generating':
                continue

            chunk_blocks = {}
            for x in range(cx * CHUNK_SIZE, (cx + 1) * CHUNK_SIZE):
                for z in range(cz * CHUNK_SIZE, (cz + 1) * CHUNK_SIZE):
                    h = self.get_height(x, z)
                    biome = self.getBiome(x, z)

                    if h > 0 and self.vegetation.has_tree(x, z, biome):
                        self.vegetation.generate(chunk_blocks, x, z, h + 1, biome)

                    block_type_top = biome
                    if biome in ["desert", "savanna"]:
                        block_type_base = biome
                    elif biome in ["tundra", "snow", "taiga"]:
                        block_type_base = "stone"
                    else:
                        block_type_base = "dirt"

                    if h < 0:
                        block_type_base = "water"
                        block_type_top = "water"
                    
                    chunk_blocks[(x, h - 1, z)] = block_type_base
                    chunk_blocks[(x, h, z)] = block_type_top
            
            self.blocks.update(chunk_blocks)
            self.chunks[(cx, cz)] = {'blocks': chunk_blocks, 'status': 'generated'}
            self.chunk_meshing_queue.put((cx, cz))

    def sprite_generation_worker(self):
        while True:
            cx, cz, player_chunk_x, player_chunk_z = self.sprite_generation_queue.get()
            if (cx, cz) in self.sprite_chunks and self.sprite_chunks[(cx, cz)].get('status') in ['generating', 'generated']:
                continue

            if abs(cx - player_chunk_x) <= SPRITE_RENDER_DISTANCE and abs(cz - player_chunk_z) <= SPRITE_RENDER_DISTANCE:
                sprites_in_chunk = self.sprites.generate_for_chunk(cx, cz, self.get_height, self.getBiome)
                if sprites_in_chunk:
                    self.sprite_chunks[(cx, cz)] = {'sprites': sprites_in_chunk, 'status': 'generated'}
                    self.sprite_meshing_queue.put((cx, cz))
                else:
                    self.sprite_chunks.pop((cx, cz), None)

    def update(self, dt, player_pos):
        chunk_x = int(player_pos[0] // CHUNK_SIZE)
        chunk_z = int(player_pos[2] // CHUNK_SIZE)

        # Génération des chunks de terrain
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                cx, cz = chunk_x + dx, chunk_z + dz
                if (cx, cz) not in self.chunks:
                    self.chunks[(cx, cz)] = {'status': 'generating'}
                    self.chunk_generation_queue.put((cx, cz, chunk_x, chunk_z))

        # Génération des sprites (par chunk)
        for dx in range(-SPRITE_RENDER_DISTANCE, SPRITE_RENDER_DISTANCE + 1):
            for dz in range(-SPRITE_RENDER_DISTANCE, SPRITE_RENDER_DISTANCE + 1):
                cx, cz = chunk_x + dx, chunk_z + dz
                if (cx, cz) not in self.sprite_chunks or self.sprite_chunks[(cx, cz)].get('status') not in ['queued', 'generating', 'generated']:
                    self.sprite_chunks[(cx, cz)] = {'status': 'queued'}
                    self.sprite_generation_queue.put((cx, cz, chunk_x, chunk_z))

        # Mise à jour des animaux (par entité)
        world_info_funcs = {
            "get_height": self.get_height,
            "get_biome": self.getBiome,
            "is_solid": self.is_solid
        }
        self.animals.update(dt, player_pos, world_info_funcs)
        animal_render_data = self.animals.get_render_data()
        if animal_render_data:
            mesh_data = self.build_sprite_mesh(animal_render_data, perpendicular=False)
            self.create_animal_batches(mesh_data)
        else:
            self.animal_batches.clear()

        # Meshing du terrain
        if not self.chunk_meshing_queue.empty():
            cx, cz = self.chunk_meshing_queue.get()
            chunk_data = self.chunks.get((cx, cz))
            if chunk_data and chunk_data.get('status') == 'generated':
                chunk_data['status'] = 'meshing'
                mesh_data = self.build_chunk_mesh(cx, cz)
                self.create_chunk_batches(cx, cz, mesh_data)
                chunk_data['status'] = 'rendered'

        # Meshing des sprites
        if not self.sprite_meshing_queue.empty():
            cx, cz = self.sprite_meshing_queue.get()
            sprite_chunk_data = self.sprite_chunks.get((cx, cz))
            if sprite_chunk_data and sprite_chunk_data.get('status') == 'generated':
                mesh_data = self.build_sprite_mesh(sprite_chunk_data['sprites'], perpendicular=True)
                self.create_sprite_batches(cx, cz, mesh_data)
                sprite_chunk_data['status'] = 'meshed'

        self.cleanup_chunks(player_pos)

    def build_chunk_mesh(self, cx, cz):
        # ... (code inchangé)
        chunk_data = self.chunks.get((cx, cz))
        if not chunk_data or 'blocks' not in chunk_data:
            return {}

        vertex_data_by_texture = {}
        
        faces = [
            ("front", ((-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5))),
            ("back", ((0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5))),
            ("left", ((-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5))),
            ("right", ((0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5))),
            ("top", ((-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5))),
            ("bottom", ((-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, -0.5, 0.5), (-0.5, -0.5, 0.5)))
        ]
        
        tex_coords = {
            "front": (0, 0, 1, 0, 1, 1, 0, 1),
            "back": (1, 0, 0, 0, 0, 1, 1, 1),
            "left": (1, 0, 0, 0, 0, 1, 1, 1),
            "right": (0, 0, 1, 0, 1, 1, 0, 1),
            "top": (0, 1, 1, 1, 1, 0, 0, 0),
            "bottom": (0, 0, 1, 0, 1, 1, 0, 1)
        }

        for (x, y, z), block_type in chunk_data['blocks'].items():
            texture = self.textures.get(block_type)
            if texture is None: continue
            if texture not in vertex_data_by_texture: vertex_data_by_texture[texture] = {'positions': [], 'tex_coords': [], 'indices': [], 'colors': [], 'count': 0}
            mesh_data = vertex_data_by_texture[texture]
            for face_name, face_verts in faces:
                direction = self.get_direction_from_face_name(face_name)
                neighbor_pos = (x + direction[0], y + direction[1], z + direction[2])
                if self.blocks.get(neighbor_pos, 'air') != 'air': continue
                for vert in face_verts: mesh_data['positions'].extend((x + vert[0], y + vert[1], z + vert[2]))
                mesh_data['tex_coords'].extend(tex_coords[face_name])
                mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4)
                vc = mesh_data['count']
                mesh_data['indices'].extend((vc, vc + 1, vc + 2, vc, vc + 2, vc + 3))
                mesh_data['count'] += 4
        return vertex_data_by_texture

    def build_sprite_mesh(self, sprites_in_chunk, perpendicular=True):
        vertex_data_by_texture = {}
        sprite_quad_vertices = [(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 1.0, 0.0), (-0.5, 1.0, 0.0)]
        sprite_tex_coords = (0, 0, 1, 0, 1, 1, 0, 1)
        sprite_indices = (0, 1, 2, 0, 2, 3)

        y_offset = 0
        if not perpendicular: # C'est un animal
            y_offset = -0.5

        for sprite_data in sprites_in_chunk:
            x, y, z = sprite_data["position"]
            sprite_type = sprite_data["type"]
            texture = self.textures.get(sprite_type)
            if texture is None: continue
            if texture not in vertex_data_by_texture: vertex_data_by_texture[texture] = {'positions': [], 'tex_coords': [], 'indices': [], 'colors': [], 'count': 0}
            mesh_data = vertex_data_by_texture[texture]
            
            vc = mesh_data['count']

            # Logique pour les animaux (plan unique orienté)
            if not perpendicular:
                velocity = sprite_data.get("velocity", [0, 0, 0])
                vx, _, vz = velocity
                
                # Calculer l'angle de rotation sur l'axe Y
                if abs(vx) > 0.01 or abs(vz) > 0.01:
                    angle = math.atan2(vx, vz)
                else:
                    angle = 0 # Pas de mouvement, pas de rotation

                cos_a = math.cos(angle)
                sin_a = math.sin(angle)

                rotated_vertices = []
                for v_x, v_y, v_z in sprite_quad_vertices:
                    # Rotation 2D sur le plan XZ
                    rotated_x = v_x * cos_a
                    rotated_z = v_x * sin_a
                    # Ajouter la position du monde
                    rotated_vertices.append((x + rotated_x, y + v_y + y_offset, z + rotated_z))

                for vert in rotated_vertices:
                    mesh_data['positions'].extend(vert)
                
                mesh_data['tex_coords'].extend(sprite_tex_coords)
                mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4)
                mesh_data['indices'].extend((vc + i for i in sprite_indices))
                mesh_data['count'] += 4

            # Logique pour la végétation (croix 3D)
            else:
                # Premier quad
                for vert in sprite_quad_vertices: mesh_data['positions'].extend((x + vert[0], y + vert[1] + y_offset, z + vert[2]))
                mesh_data['tex_coords'].extend(sprite_tex_coords)
                mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4)
                mesh_data['indices'].extend((vc + i for i in sprite_indices))
                mesh_data['count'] += 4

                # Deuxième quad perpendiculaire
                sprite_quad_vertices_2 = [(0.0, 0.0, -0.5), (0.0, 0.0, 0.5), (0.0, 1.0, 0.5), (0.0, 1.0, -0.5)]
                vc_perp = mesh_data['count']
                sprite_indices_2 = (vc_perp, vc_perp + 1, vc_perp + 2, vc_perp, vc_perp + 2, vc_perp + 3)
                for vert in sprite_quad_vertices_2: mesh_data['positions'].extend((x + vert[0], y + vert[1] + y_offset, z + vert[2]))
                mesh_data['tex_coords'].extend(sprite_tex_coords)
                mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4)
                mesh_data['indices'].extend(sprite_indices_2)
                mesh_data['count'] += 4

        return vertex_data_by_texture

    def get_direction_from_face_name(self, face_name):
        # ... (code inchangé)
        if face_name == "front": return (0, 0, 1)
        if face_name == "back": return (0, 0, -1)
        if face_name == "left": return (-1, 0, 0)
        if face_name == "right": return (1, 0, 0)
        if face_name == "top": return (0, 1, 0)
        if face_name == "bottom": return (0, -1, 0)
        return (0, 0, 0)

    def create_chunk_batches(self, cx, cz, mesh_data_by_texture):
        self.chunk_batches[(cx, cz)] = {}
        for texture, mesh_data in mesh_data_by_texture.items():
            if not mesh_data['indices']: continue
            batch = pyglet.graphics.Batch()
            self.program.vertex_list_indexed(mesh_data['count'], pyglet.gl.GL_TRIANGLES, mesh_data['indices'], batch, None, position=('f', mesh_data['positions']), tex_coords=('f', mesh_data['tex_coords']), colors=('f', mesh_data['colors']))
            self.chunk_batches[(cx, cz)][texture] = batch

    def create_sprite_batches(self, cx, cz, mesh_data_by_texture):
        self.sprite_batches[(cx, cz)] = {}
        for texture, mesh_data in mesh_data_by_texture.items():
            if not mesh_data['indices']: continue
            batch = pyglet.graphics.Batch()
            self.program.vertex_list_indexed(mesh_data['count'], pyglet.gl.GL_TRIANGLES, mesh_data['indices'], batch, None, position=('f', mesh_data['positions']), tex_coords=('f', mesh_data['tex_coords']), colors=('f', mesh_data['colors']))
            self.sprite_batches[(cx, cz)][texture] = batch

    def create_animal_batches(self, mesh_data_by_texture):
        """Crée les batches pour les animaux (non lié à un chunk)."""
        self.animal_batches.clear()
        for texture, mesh_data in mesh_data_by_texture.items():
            if not mesh_data['indices']: continue
            batch = pyglet.graphics.Batch()
            self.program.vertex_list_indexed(mesh_data['count'], pyglet.gl.GL_TRIANGLES, mesh_data['indices'], batch, None, position=('f', mesh_data['positions']), tex_coords=('f', mesh_data['tex_coords']), colors=('f', mesh_data['colors']))
            self.animal_batches[texture] = batch

    def get_biome_label(self, player_pos):
        # ... (code inchangé)
        biome = self.getBiome(player_pos[0], player_pos[2])
        return f"Biome: {biome.capitalize()}"

    def get_height(self, x, z):
        # ... (code inchangé)
        base = noise.pnoise2(x * 0.01, z * 0.01, octaves=3, base=WORLD_SEED) * 50
        detail = noise.pnoise2(x * 0.1, z * 0.1, octaves=2, base=WORLD_SEED) * 5
        return int(base + detail - 5) + 10

    def cleanup_chunks(self, player_pos):
        to_delete = []
        player_chunk_x = int(player_pos[0] // CHUNK_SIZE)
        player_chunk_z = int(player_pos[2] // CHUNK_SIZE)

        for (cx, cz) in list(self.chunks.keys()):
            if abs(cx - player_chunk_x) > RENDER_DISTANCE + 2 or abs(cz - player_chunk_z) > RENDER_DISTANCE + 2:
                to_delete.append((cx, cz))

        for key in to_delete:
            self.chunks.pop(key, None)
            self.chunk_batches.pop(key, None)
            self.sprite_chunks.pop(key, None)
            self.sprite_batches.pop(key, None)

    def draw(self, player_pos):
        player_chunk_x = int(player_pos[0] // CHUNK_SIZE)
        player_chunk_z = int(player_pos[2] // CHUNK_SIZE)

        # Dessin des chunks
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                cx, cz = player_chunk_x + dx, player_chunk_z + dz
                if (cx, cz) in self.chunk_batches:
                    for texture, batch in self.chunk_batches[(cx, cz)].items():
                        pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
                        pyglet.gl.glBindTexture(texture.target, texture.id)
                        self.program['our_texture'] = 0
                        batch.draw()

        # Dessin des sprites et animaux
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
        pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE)

        # Dessin des sprites (par chunk)
        for dx in range(-SPRITE_RENDER_DISTANCE, SPRITE_RENDER_DISTANCE + 1):
            for dz in range(-SPRITE_RENDER_DISTANCE, SPRITE_RENDER_DISTANCE + 1):
                cx, cz = player_chunk_x + dx, player_chunk_z + dz
                if (cx, cz) in self.sprite_batches:
                    for texture, batch in self.sprite_batches[(cx, cz)].items():
                        pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
                        pyglet.gl.glBindTexture(texture.target, texture.id)
                        self.program['our_texture'] = 0
                        batch.draw()
        
        # Dessin des animaux (batch unique)
        for texture, batch in self.animal_batches.items():
            pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
            pyglet.gl.glBindTexture(texture.target, texture.id)
            self.program['our_texture'] = 0
            batch.draw()

        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glDisable(pyglet.gl.GL_BLEND)

    def normalize_to_uniform_simple(self, noise_value):
        # ... (code inchangé)
        normalized = (noise_value + 1) / 2
        if normalized < 0.5: return 2 * (normalized ** 1.5)
        else: return 1 - 2 * ((1-normalized) ** 1.5)

    def getBiome(self, x, z, biome_scale=1000.0):
        # ... (code inchangé)
        seed=WORLD_SEED
        octaves=8
        temp_raw = 0.7 * noise.pnoise2(x/biome_scale, z/biome_scale, octaves=octaves, base=seed) + 0.3 * noise.pnoise2(x/(biome_scale/5), z/(biome_scale/5), octaves=5, base=seed+50)
        humid_raw = 0.7 * noise.pnoise2((x+1000)/biome_scale, (z+1000)/biome_scale, octaves=octaves, base=seed+10) + 0.3 * noise.pnoise2((x+1000)/(biome_scale/5), (z+1000)/(biome_scale/5), octaves=5, base=seed+60)
        temp = self.normalize_to_uniform_simple(temp_raw)
        humid = self.normalize_to_uniform_simple(humid_raw)
        if temp < 0.35: return "snow"
        elif temp < 0.55:
            if humid < 0.3: return "taiga"
            elif humid < 0.7: return "forest"
            else: return "plains"
        elif temp < 0.65:
            if humid < 0.6: return "savanna"
            else: return "desert"
        else:
            if humid < 0.6: return "desert"
            else: return "jungle"

    def is_solid(self, position):
        """Vérifie si un bloc à une position donnée est solide (y compris l'eau)."""
        block_type = self.blocks.get(position)
        return block_type is not None
