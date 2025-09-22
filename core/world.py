import threading, queue, math
import pyglet
import noise
from core.textures import Textures
from core.vegetation import Vegetation
from core.sprites import Sprites
from core.animals import Animals # Importer la nouvelle classe
from config import CHUNK_SIZE, RENDER_DISTANCE, WORLD_SEED, SPRITE_RENDER_DISTANCE

class World:
    def __init__(self, program, seed=WORLD_SEED):
        self.program = program
        self.seed = seed
        self.blocks = {}
        self.chunks = {}
        self.chunk_batches = {}

        self.chunk_generation_queue = queue.Queue()
        self.chunk_batch_creation_queue = queue.Queue()

        self.textures = Textures()
        self.vegetation = Vegetation(seed=self.seed)

        # Système de sprites (basé sur les chunks)
        self.sprites = Sprites(seed=self.seed, vegetation=self.vegetation, textures=self.textures)
        self.sprite_chunks = {}
        self.sprite_batches = {}
        self.sprite_generation_queue = queue.Queue()
        self.sprite_batch_creation_queue = queue.Queue()

        # Système d'animaux (basé sur des entités)
        self.animals = Animals(seed=self.seed, vegetation=self.vegetation, program=self.program)
        self.animals.set_textures(self.textures)

        self.destroyed_blocks = set()

        # Démarrer les workers pour le terrain et les sprites
        threading.Thread(target=self.chunk_generation_worker, daemon=True).start()
        threading.Thread(target=self.sprite_generation_worker, daemon=True).start()

    def chunk_generation_worker(self):
        while True:
            cx, cz, player_chunk_x, player_chunk_z = self.chunk_generation_queue.get()
            if (cx, cz) in self.chunks and self.chunks[(cx, cz)].get('status') != 'generating':
                continue

            chunk_blocks = {}

            # Pre-calculate heights in and around the chunk to avoid redundant noise calls
            surface_heights = {}
            for local_x in range(-1, CHUNK_SIZE + 1):
                for local_z in range(-1, CHUNK_SIZE + 1):
                    world_x, world_z = cx * CHUNK_SIZE + local_x, cz * CHUNK_SIZE + local_z
                    surface_heights[(world_x, world_z)] = self.get_height(world_x, world_z)

            for x in range(cx * CHUNK_SIZE, (cx + 1) * CHUNK_SIZE):
                for z in range(cz * CHUNK_SIZE, (cz + 1) * CHUNK_SIZE):
                    h = surface_heights.get((x, z), 0)
                    biome_info = self.get_biome(x, z)
                    biome = biome_info["name"]

                    # Determine block types based on biome
                    block_type_top = biome
                    if biome in ["desert", "savanna"]:
                        block_type_base = biome
                    elif biome in ["tundra", "snow", "taiga"]:
                        block_type_base = "stone"
                    else:
                        block_type_base = "dirt"

                    if h < 0:
                        block_type_top = "water"
                        block_type_base = "water"

                    # Generate the surface block
                    chunk_blocks[(x, h, z)] = block_type_top

                    # Generate trees on the surface
                    if h > 0 and self.vegetation.has_tree(x, z, biome):
                        self.vegetation.generate(chunk_blocks, x, z, h + 1, biome)

                    # Get neighbor heights from the pre-calculated map
                    h_xp = surface_heights.get((x + 1, z), h)
                    h_xm = surface_heights.get((x - 1, z), h)
                    h_zp = surface_heights.get((x, z + 1), h)
                    h_zm = surface_heights.get((x, z - 1), h)

                    # Find the minimum height among the column and its direct neighbors
                    min_neighbor_h = min(h, h_xp, h_xm, h_zp, h_zm)

                    # Fill downwards from the surface to seal any side-holes
                    for y in range(h - 1, min_neighbor_h - 1, -1):
                        chunk_blocks[(x, y, z)] = block_type_base if y >= 0 else "water"

            # Carve caves using 3D noise
            for pos in list(chunk_blocks.keys()):
                x, y, z = pos
                surface_h = surface_heights.get((x, z), 0)
                # Don't carve near the surface or in water
                if y >= surface_h - 3 or y < 0:
                    continue

                # 3D noise for caves
                cave_noise = noise.pnoise3(x * 0.05, y * 0.05, z * 0.05, octaves=2, base=self.seed + 2)

                if cave_noise > 0.6:
                    del chunk_blocks[pos]

            self.blocks.update(chunk_blocks)
            self.chunks[(cx, cz)] = {'blocks': chunk_blocks, 'status': 'meshing'}

            mesh_data = self.build_chunk_mesh(cx, cz)
            self.chunk_batch_creation_queue.put((cx, cz, mesh_data))

    def sprite_generation_worker(self):
        while True:
            cx, cz, player_chunk_x, player_chunk_z = self.sprite_generation_queue.get()
            if (cx, cz) in self.sprite_chunks and self.sprite_chunks[(cx, cz)].get('status') not in ['queued', 'generating']:
                continue

            if abs(cx - player_chunk_x) <= SPRITE_RENDER_DISTANCE and abs(cz - player_chunk_z) <= SPRITE_RENDER_DISTANCE:
                self.sprite_chunks[(cx, cz)] = {'status': 'generating'}
                sprites_in_chunk = self.sprites.generate_for_chunk(cx, cz, self.get_height, self.get_biome_name)

                if sprites_in_chunk:
                    self.sprite_chunks[(cx, cz)]['sprites'] = sprites_in_chunk
                    self.sprite_chunks[(cx, cz)]['status'] = 'meshing'
                    mesh_data = self.build_sprite_mesh(sprites_in_chunk, perpendicular=True)
                    self.sprite_batch_creation_queue.put((cx, cz, mesh_data))
                else:
                    self.sprite_chunks[(cx, cz)]['status'] = 'empty'

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
                if (cx, cz) not in self.sprite_chunks:
                    self.sprite_chunks[(cx, cz)] = {'status': 'queued'}
                    self.sprite_generation_queue.put((cx, cz, chunk_x, chunk_z))

        # Mise à jour des animaux (par entité)
        world_info_funcs = {
            "get_height": self.get_height,
            "get_biome": self.get_biome_name,
            "is_solid": self.is_solid
        }
        self.animals.update(dt, player_pos, world_info_funcs)

        # Création des batches de terrain (depuis le worker)
        while not self.chunk_batch_creation_queue.empty():
            cx, cz, mesh_data = self.chunk_batch_creation_queue.get()
            chunk_data = self.chunks.get((cx, cz))
            if chunk_data:
                self.create_chunk_batches(cx, cz, mesh_data)
                chunk_data['status'] = 'rendered'

        # Création des batches de sprites (depuis le worker)
        while not self.sprite_batch_creation_queue.empty():
            cx, cz, mesh_data = self.sprite_batch_creation_queue.get()
            sprite_chunk_data = self.sprite_chunks.get((cx, cz))
            if sprite_chunk_data:
                self.create_sprite_batches(cx, cz, mesh_data)
                sprite_chunk_data['status'] = 'rendered'

        self.cleanup_chunks(player_pos)

    def _rebuild_chunk(self, cx, cz):
        # Re-mesh the chunk and update its batch. This is synchronous.
        if (cx, cz) in self.chunks:
            mesh_data = self.build_chunk_mesh(cx, cz)
            self.create_chunk_batches(cx, cz, mesh_data)

    def add_block(self, pos, block_type):
        # If this position was previously destroyed, un-destroy it.
        self.destroyed_blocks.discard(pos)

        x, y, z = pos
        cx, cz = int(x // CHUNK_SIZE), int(z // CHUNK_SIZE)

        # Add to global and chunk-specific block lists
        self.blocks[pos] = block_type
        if (cx, cz) in self.chunks and 'blocks' in self.chunks[(cx, cz)]:
            self.chunks[(cx, cz)]['blocks'][pos] = block_type

        # Rebuild the chunk that contains the new block
        self._rebuild_chunk(cx, cz)

        # Check if the block is on a chunk boundary and rebuild neighbors if so
        if x % CHUNK_SIZE == 0:
            self._rebuild_chunk(cx - 1, cz)
        elif x % CHUNK_SIZE == CHUNK_SIZE - 1:
            self._rebuild_chunk(cx + 1, cz)
        if z % CHUNK_SIZE == 0:
            self._rebuild_chunk(cx, cz - 1)
        elif z % CHUNK_SIZE == CHUNK_SIZE - 1:
            self._rebuild_chunk(cx, cz + 1)

    def remove_block(self, pos):
        if pos not in self.blocks:
            return

        # Add to the set of destroyed blocks before doing anything else
        self.destroyed_blocks.add(pos)

        x, y, z = pos

        # 1. Delete the block
        del self.blocks[pos]
        cx, cz = int(x // CHUNK_SIZE), int(z // CHUNK_SIZE)
        if (cx, cz) in self.chunks and 'blocks' in self.chunks[(cx, cz)] and pos in self.chunks[(cx, cz)]['blocks']:
            del self.chunks[(cx, cz)]['blocks'][pos]

        # 2. Check and generate all 6 neighbors if they are now exposed and should exist
        neighbors = [
            (x + 1, y, z), (x - 1, y, z),
            (x, y + 1, z), (x, y - 1, z),
            (x, y, z + 1), (x, y, z - 1)
        ]
        for n_pos in neighbors:
            self._check_and_generate_block_at(n_pos)

        # 3. Rebuild all chunks affected by the change
        chunks_to_rebuild = {(cx, cz)}
        for n_pos in neighbors:
            ncx, ncz = int(n_pos[0] // CHUNK_SIZE), int(n_pos[2] // CHUNK_SIZE)
            chunks_to_rebuild.add((ncx, ncz))

        for chunk_coord in chunks_to_rebuild:
            self._rebuild_chunk(chunk_coord[0], chunk_coord[1])

    def _check_and_generate_block_at(self, pos):
        if pos in self.destroyed_blocks or pos in self.blocks:
            return # Block was destroyed by player or already exists

        x, y, z = pos

        # A block should be generated if it's below the natural surface
        # and is exposed to an existing air block.
        h = self.get_height(x, z)
        if y > h:
            return # Above natural surface

        # Check for exposure to air
        is_exposed = False
        neighbors = [
            (x + 1, y, z), (x - 1, y, z),
            (x, y + 1, z), (x, y - 1, z),
            (x, y, z + 1), (x, y, z - 1)
        ]
        for n_pos in neighbors:
            if n_pos not in self.blocks:
                is_exposed = True
                break

        if not is_exposed:
            return # Not exposed, no need to generate

        # If we get here, the block is missing, not player-destroyed, below the surface, and exposed.
        # We should generate it.
        biome_info = self.get_biome(x, z)
        biome = biome_info["name"]

        if y == h:
            block_type = biome if h >= 0 else "water"
        else: # y < h
            if h < 0:
                block_type = "water"
            elif biome in ["desert", "savanna"]:
                block_type = biome
            elif biome in ["tundra", "snow", "taiga"]:
                block_type = "stone"
            else:
                block_type = "dirt"

        # Add the new block to the world data
        cx, cz = int(x // CHUNK_SIZE), int(z // CHUNK_SIZE)
        self.blocks[pos] = block_type
        if (cx, cz) in self.chunks and 'blocks' in self.chunks[(cx, cz)]:
            self.chunks[(cx, cz)]['blocks'][pos] = block_type


    def build_chunk_mesh(self, cx, cz):
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
        sprite_tex_coords = (0, 0, 1, 0, 1, 1, 0, 1)
        sprite_indices = (0, 1, 2, 0, 2, 3)

        y_offset = 0
        if not perpendicular: # C'est un animal
            y_offset = -0.5

        for sprite_data in sprites_in_chunk:
            x, y, z = sprite_data["position"]
            sprite_type = sprite_data["type"]

            width = sprite_data.get("width", 1.0) if not perpendicular else 1.0
            height = sprite_data.get("height", 1.0) if not perpendicular else 1.0

            half_width = width / 2
            sprite_quad_vertices = [(-half_width, 0.0, 0.0), (half_width, 0.0, 0.0), (half_width, height, 0.0), (-half_width, height, 0.0)]

            texture = self.textures.get(sprite_type)
            if texture is None: continue
            if texture not in vertex_data_by_texture: vertex_data_by_texture[texture] = {'positions': [], 'tex_coords': [], 'indices': [], 'colors': [], 'count': 0}
            mesh_data = vertex_data_by_texture[texture]

            vc = mesh_data['count']

            if not perpendicular:
                velocity = sprite_data.get("velocity", [0, 0, 0])
                vx, _, vz = velocity

                if abs(vx) > 0.01 or abs(vz) > 0.01:
                    angle = math.atan2(vx, vz)
                else:
                    angle = 0

                cos_a = math.cos(angle)
                sin_a = math.sin(angle)

                rotated_vertices = []
                for v_x, v_y, v_z in sprite_quad_vertices:
                    rotated_x = v_x * cos_a
                    rotated_z = v_x * sin_a
                    rotated_vertices.append((x + rotated_x, y + v_y + y_offset, z + rotated_z))

                for vert in rotated_vertices:
                    mesh_data['positions'].extend(vert)

                mesh_data['tex_coords'].extend(sprite_tex_coords)
                mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4)
                mesh_data['indices'].extend((vc + i for i in sprite_indices))
                mesh_data['count'] += 4

            else:
                for vert in sprite_quad_vertices: mesh_data['positions'].extend((x + vert[0], y + vert[1] + y_offset, z + vert[2]))
                mesh_data['tex_coords'].extend(sprite_tex_coords)
                mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4)
                mesh_data['indices'].extend((vc + i for i in sprite_indices))
                mesh_data['count'] += 4

                sprite_quad_vertices_2 = [(0.0, 0.0, -half_width), (0.0, 0.0, half_width), (0.0, height, half_width), (0.0, height, -half_width)]
                vc_perp = mesh_data['count']
                sprite_indices_2 = (vc_perp, vc_perp + 1, vc_perp + 2, vc_perp, vc_perp + 2, vc_perp + 3)
                for vert in sprite_quad_vertices_2: mesh_data['positions'].extend((x + vert[0], y + vert[1] + y_offset, z + vert[2]))
                mesh_data['tex_coords'].extend(sprite_tex_coords)
                mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4)
                mesh_data['indices'].extend(sprite_indices_2)
                mesh_data['count'] += 4

        return vertex_data_by_texture

    def get_direction_from_face_name(self, face_name):
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

    def get_biome_label(self, player_pos):
        biome_name = self.get_biome_name(player_pos[0], player_pos[2])
        return f"Biome: {biome_name.capitalize()}"

    def get_height(self, x, z):
        # Base terrain noise for rolling hills
        base = noise.pnoise2(x * 0.01, z * 0.01, octaves=6, base=self.seed)

        # Mountain noise for major elevation changes
        mountain_noise = noise.pnoise2(x * 0.005, z * 0.005, octaves=4, base=self.seed + 1)

        # Remap mountain noise from [-1, 1] to a [0, 1] intensity, starting from a threshold
        # This creates a smooth transition from plains to mountains instead of a sharp cliff
        mountain_threshold = 0.2
        mountain_intensity = (mountain_noise - mountain_threshold) / (1.0 - mountain_threshold)
        mountain_intensity = max(0, mountain_intensity)

        # Shape the intensity curve to make foothills less steep and peaks more dramatic
        mountain_elevation = pow(mountain_intensity, 2) * 150

        # Combine base terrain with mountains
        final_height = (base * 20) + mountain_elevation + 10

        return int(final_height)

    def cleanup_chunks(self, player_pos):
        to_delete = []
        player_chunk_x = int(player_pos[0] // CHUNK_SIZE)
        player_chunk_z = int(player_pos[2] // CHUNK_SIZE)

        for (cx, cz) in list(self.chunks.keys()):
            if abs(cx - player_chunk_x) > RENDER_DISTANCE or abs(cz - player_chunk_z) > RENDER_DISTANCE:
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
        self.animals.draw() # Added

        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE)
        pyglet.gl.glDisable(pyglet.gl.GL_BLEND)

    def normalize_to_uniform_simple(self, noise_value):
        normalized = (noise_value + 1) / 2
        return 1 / (1 + math.exp(-10 * (normalized - 0.5)))

    def get_biome_name(self, x, z):
        return self.get_biome(x, z)["name"]

    def get_biome(self, x, z, biome_scale=1000.0):
        seed = self.seed
        octaves = 6

        temp_raw = noise.pnoise2(x / biome_scale, z / biome_scale, octaves=octaves, base=seed)
        humid_raw = noise.pnoise2((x + 1000) / biome_scale, (z + 1000) / biome_scale, octaves=octaves, base=seed + 10)

        temp = self.normalize_to_uniform_simple(temp_raw)
        humid = self.normalize_to_uniform_simple(humid_raw)

        biome_name = "plains"
        if temp < 0.35:
            if humid < 0.5:
                biome_name = "tundra"
            else:
                biome_name = "snow"
        elif temp < 0.50:
            if humid < 0.4:
                biome_name = "taiga"
            else:
                biome_name = "forest"
        elif temp < 0.60:
            if humid < 0.4:
                biome_name = "plains"
            else:
                biome_name = "forest"
        elif temp < 0.70:
            if humid < 0.40:
                biome_name = "savanna"
            else:
                biome_name = "forest"
        else:
            if humid < 0.5:
                biome_name = "desert"
            else:
                biome_name = "jungle"

        return {"name": biome_name, "temp": temp, "humid": humid}

    def get_biome_at_chunk_center(self, cx, cz):
        center_x = cx * CHUNK_SIZE + CHUNK_SIZE // 2
        center_z = cz * CHUNK_SIZE + CHUNK_SIZE // 2

        height_at_center = self.get_height(center_x, center_z)

        if height_at_center < 0:
            return "water"

        return self.get_biome_name(center_x, center_z)

    def is_solid(self, position):
        block_type = self.blocks.get(position)
        return block_type is not None
