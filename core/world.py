import threading, queue, math
import pyglet
import noise
from core.textures import Textures
from core.vegetation import Vegetation
from core.sprites import Sprites
from config import CHUNK_SIZE, RENDER_DISTANCE, WORLD_SEED, SPRITE_RENDER_DISTANCE # New import

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
        self.sprites = Sprites(seed=WORLD_SEED)
        self.sprite_chunks = {}
        self.sprite_meshing_queue = queue.Queue()
        self.sprite_batches = {}

        # Start a worker thread for chunk generation
        threading.Thread(target=self.chunk_generation_worker, daemon=True).start()

    def chunk_generation_worker(self):
        while True:
            cx, cz, player_chunk_x, player_chunk_z = self.chunk_generation_queue.get() # Modified
            if (cx, cz) in self.chunks and self.chunks[(cx, cz)].get('status') != 'generating':
                continue # Already generated or queued for meshing

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
            
            self.chunks[(cx, cz)] = {
                'blocks': chunk_blocks,
                'status': 'generated'
            }
            self.chunk_meshing_queue.put((cx, cz))

            # New: Generate sprites for this chunk if within SPRITE_RENDER_DISTANCE
            # This check is important to avoid generating sprites for chunks that are too far
            # even if the main world generation goes further.
            # Accessing player position from self.program.player might be problematic in a worker thread
            # if player object is not thread-safe or not yet initialized.
            # For now, assuming it's safe or will be handled.
            # A more robust solution would be to pass player_pos to chunk_generation_worker or
            # have a separate sprite generation queue that is processed in the main thread.
            if abs(cx - player_chunk_x) <= SPRITE_RENDER_DISTANCE and \
               abs(cz - player_chunk_z) <= SPRITE_RENDER_DISTANCE:
                sprites_in_chunk = self.sprites.generate_for_chunk(cx, cz, chunk_blocks, self.getBiome)
                if sprites_in_chunk:
                    self.sprite_chunks[(cx, cz)] = sprites_in_chunk
                    self.sprite_meshing_queue.put((cx, cz))


    def update(self, player_pos):
        chunk_x = int(player_pos[0] // CHUNK_SIZE)
        chunk_z = int(player_pos[2] // CHUNK_SIZE)

        # Enqueue new chunks to be generated (for world blocks)
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                cx, cz = chunk_x + dx, chunk_z + dz
                if (cx, cz) not in self.chunks:
                    self.chunks[(cx, cz)] = {'status': 'generating'}
                    self.chunk_generation_queue.put((cx, cz, chunk_x, chunk_z)) # Added chunk_x, chunk_z

        # Process one chunk from the meshing queue per frame to avoid lag spikes
        if not self.chunk_meshing_queue.empty():
            cx, cz = self.chunk_meshing_queue.get()
            chunk_data = self.chunks.get((cx, cz))
            if chunk_data and chunk_data.get('status') == 'generated':
                chunk_data['status'] = 'meshing'
                mesh_data = self.build_chunk_mesh(cx, cz)
                self.create_chunk_batches(cx, cz, mesh_data)
                chunk_data['status'] = 'rendered'

        # Process one sprite chunk from the meshing queue
        if not self.sprite_meshing_queue.empty():
            cx, cz = self.sprite_meshing_queue.get()
            sprite_data = self.sprite_chunks.get((cx, cz))
            if sprite_data:
                mesh_data = self.build_sprite_mesh(cx, cz, sprite_data)
                self.create_sprite_batches(cx, cz, mesh_data)


        self.cleanup_chunks(player_pos)

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
        
        # Correct texture coordinates for a single texture applied to all faces
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
            if texture is None:
                continue

            if texture not in vertex_data_by_texture:
                vertex_data_by_texture[texture] = {'positions': [], 'tex_coords': [], 'indices': [], 'colors': [], 'count': 0}
            
            mesh_data = vertex_data_by_texture[texture]

            for face_name, face_verts in faces:
                direction = self.get_direction_from_face_name(face_name)
                neighbor_pos = (x + direction[0], y + direction[1], z + direction[2])
                if self.blocks.get(neighbor_pos, 'air') != 'air': # Simple occlusion culling
                    continue

                for vert in face_verts:
                    mesh_data['positions'].extend((x + vert[0], y + vert[1], z + vert[2]))
                
                mesh_data['tex_coords'].extend(tex_coords[face_name])
                mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4) # Add white color for each vertex

                vc = mesh_data['count']
                mesh_data['indices'].extend((vc, vc + 1, vc + 2, vc, vc + 2, vc + 3))
                mesh_data['count'] += 4
        
        return vertex_data_by_texture

    def build_sprite_mesh(self, cx, cz, sprites_in_chunk):
        vertex_data_by_texture = {}

        # Sprite is a 2D quad that always faces the camera (billboard)
        # Vertices for a quad centered at (0,0,0) with size 1x1
        # We will translate these to the sprite's position later in the shader or here
        # For now, let's define a simple quad that will be scaled and positioned
        # The actual billboard effect will be handled by the shader
        sprite_quad_vertices = [
            (-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 1.0, 0.0), (-0.5, 1.0, 0.0) # Bottom-left, Bottom-right, Top-right, Top-left
        ]
        sprite_tex_coords = (0, 0, 1, 0, 1, 1, 0, 1) # Standard texture coordinates for a quad
        sprite_indices = (0, 1, 2, 0, 2, 3) # Two triangles for a quad

        for sprite in sprites_in_chunk:
            x, y, z = sprite["position"]
            sprite_type = sprite["type"]
            
            texture = self.textures.get(sprite_type) # Get texture for sprite type
            if texture is None:
                continue

            if texture not in vertex_data_by_texture:
                vertex_data_by_texture[texture] = {'positions': [], 'tex_coords': [], 'indices': [], 'colors': [], 'count': 0}
            
            mesh_data = vertex_data_by_texture[texture]

            # Add vertices for the sprite quad, translated to its world position
            for vert in sprite_quad_vertices:
                mesh_data['positions'].extend((x + vert[0], y + vert[1], z + vert[2]))
            
            mesh_data['tex_coords'].extend(sprite_tex_coords)
            mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4) # White color for each vertex

            vc = mesh_data['count']
            mesh_data['indices'].extend((vc, vc + 1, vc + 2, vc, vc + 2, vc + 3))
            mesh_data['count'] += 4
        
        return vertex_data_by_texture

    def get_direction_from_face_name(self, face_name):
        if face_name == "front":
            return (0, 0, 1)
        elif face_name == "back":
            return (0, 0, -1)
        elif face_name == "left":
            return (-1, 0, 0)
        elif face_name == "right":
            return (1, 0, 0)
        elif face_name == "top":
            return (0, 1, 0)
        elif face_name == "bottom":
            return (0, -1, 0)
        return (0, 0, 0)

    def create_chunk_batches(self, cx, cz, mesh_data_by_texture):
        self.chunk_batches[(cx, cz)] = {}
        for texture, mesh_data in mesh_data_by_texture.items():
            if not mesh_data['indices']:
                continue

            batch = pyglet.graphics.Batch()
            
            # Create a vertex list and add it to the batch.
            # The vertex list is created by the shader program.
            self.program.vertex_list_indexed(
                mesh_data['count'],
                pyglet.gl.GL_TRIANGLES,
                mesh_data['indices'],
                batch,
                None,
                # Map shader attribute names to data tuples (format, array)
                position=('f', mesh_data['positions']),
                tex_coords=('f', mesh_data['tex_coords']),
                colors=('f', mesh_data['colors'])
            )

            self.chunk_batches[(cx, cz)][texture] = batch

    def create_sprite_batches(self, cx, cz, mesh_data_by_texture):
        self.sprite_batches[(cx, cz)] = {}
        for texture, mesh_data in mesh_data_by_texture.items():
            if not mesh_data['indices']:
                continue

            batch = pyglet.graphics.Batch()
            
            self.program.vertex_list_indexed(
                mesh_data['count'],
                pyglet.gl.GL_TRIANGLES,
                mesh_data['indices'],
                batch,
                None,
                position=('f', mesh_data['positions']),
                tex_coords=('f', mesh_data['tex_coords']),
                colors=('f', mesh_data['colors'])
            )

            self.sprite_batches[(cx, cz)][texture] = batch

    def get_biome_label(self, player_pos):
        biome = self.getBiome(player_pos[0], player_pos[2])
        return f"Biome: {biome.capitalize()}"

    def get_height(self, x, z):
        base = noise.pnoise2(x * 0.01, z * 0.01, octaves=3, base=WORLD_SEED) * 50
        detail = noise.pnoise2(x * 0.1, z * 0.1, octaves=2, base=WORLD_SEED) * 5
        return int(base + detail - 5) + 10

    def cleanup_chunks(self, player_pos):
        to_delete = []
        player_chunk_x = int(player_pos[0] // CHUNK_SIZE)
        player_chunk_z = int(player_pos[2] // CHUNK_SIZE)

        for (cx, cz) in self.chunks:
            if abs(cx - player_chunk_x) > RENDER_DISTANCE + 2 or abs(cz - player_chunk_z) > RENDER_DISTANCE + 2:
                to_delete.append((cx, cz))

        for key in to_delete:
            chunk_data = self.chunks.pop(key, {})
            if chunk_data.get('blocks'):
                for pos in chunk_data['blocks']:
                    self.blocks.pop(pos, None)
            self.chunk_batches.pop(key, None)
            self.sprite_chunks.pop(key, None)
            self.sprite_batches.pop(key, None)

    def draw(self, player_pos):
        player_chunk_x = int(player_pos[0] // CHUNK_SIZE)
        player_chunk_z = int(player_pos[2] // CHUNK_SIZE)

        # Draw regular chunks
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                cx, cz = player_chunk_x + dx, player_chunk_z + dz
                
                if (cx, cz) not in self.chunk_batches:
                    continue
                
                batches = self.chunk_batches[(cx, cz)]
                for texture, batch in batches.items():
                    pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
                    pyglet.gl.glBindTexture(texture.target, texture.id)
                    self.program['our_texture'] = 0
                    batch.draw()

        # New: Draw sprites
        # Enable blending for transparency
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
        pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE) # Disable culling for sprites

        for dx in range(-SPRITE_RENDER_DISTANCE, SPRITE_RENDER_DISTANCE + 1):
            for dz in range(-SPRITE_RENDER_DISTANCE, SPRITE_RENDER_DISTANCE + 1):
                cx, cz = player_chunk_x + dx, player_chunk_z + dz
                
                if (cx, cz) not in self.sprite_batches:
                    continue
                
                batches = self.sprite_batches[(cx, cz)]
                for texture, batch in batches.items():
                    pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
                    pyglet.gl.glBindTexture(texture.target, texture.id)
                    self.program['our_texture'] = 0
                    batch.draw()
        
        pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE) # Re-enable culling
        pyglet.gl.glDisable(pyglet.gl.GL_BLEND) # Disable blending after drawing sprites

    def normalize_to_uniform_simple(self, noise_value):
        normalized = (noise_value + 1) / 2
        if normalized < 0.5:
            return 2 * (normalized ** 1.5)
        else:
            return 1 - 2 * ((1-normalized) ** 1.5)

    def getBiome(self, x, z, biome_scale=1000.0):
        seed=WORLD_SEED
        octaves=8
        temp_raw = 0.7 * noise.pnoise2(x/biome_scale, z/biome_scale, octaves=octaves, base=seed) + 0.3 * noise.pnoise2(x/(biome_scale/5), z/(biome_scale/5), octaves=5, base=seed+50)
        humid_raw = 0.7 * noise.pnoise2((x+1000)/biome_scale, (z+1000)/biome_scale, octaves=octaves, base=seed+10) + 0.3 * noise.pnoise2((x+1000)/(biome_scale/5), (z+1000)/(biome_scale/5), octaves=5, base=seed+60)
        
        temp = self.normalize_to_uniform_simple(temp_raw)
        humid = self.normalize_to_uniform_simple(humid_raw)
        
        if temp < 0.35:
            return "snow"
        elif temp < 0.55:
            if humid < 0.3:
                return "taiga"
            elif humid < 0.7:
                return "forest"
            else:
                return "plains"
        elif temp < 0.65:
            if humid < 0.6:
                return "savanna"
            else:
                return "desert"
        else:
            if humid < 0.6:
                return "desert"
            else:
                return "jungle"

    def is_solid(self, position):
        """Vérifie si un bloc à une position donnée est solide (y compris l'eau)."""
        block_type = self.blocks.get(position)
        return block_type is not None