import threading, queue, math
import pyglet
import noise
from pyglet.gl import *
from config import CHUNK_SIZE, RENDER_DISTANCE, BLOCK_HEIGHT, WORLD_SEED
from core.textures import Textures

class World:
    def __init__(self):
        self.blocks = {}
        self.chunks = {}
        self.chunk_batches = {}
        self.chunks_to_update = []
        self.chunk_queue = queue.Queue()
        self.textures = Textures()



    def update(self, player_pos):
        chunk_x = int(player_pos[0] // CHUNK_SIZE)
        chunk_z = int(player_pos[2] // CHUNK_SIZE)

        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE+1):
            for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE+1):
                cx, cz = chunk_x + dx, chunk_z + dz
                if (cx, cz) not in self.chunks:
                    threading.Thread(target=self.generate_chunk_thread, args=(cx, cz), daemon=True).start()

        while not self.chunk_queue.empty():
            cx, cz, chunk_blocks = self.chunk_queue.get()
            pending = list(chunk_blocks.items())
            self.chunks[(cx, cz)] = {'blocks': chunk_blocks, 'pending': pending}
            self.chunks_to_update.append((cx, cz))
            self.chunk_batches[(cx, cz)] = (pyglet.graphics.Batch(), pyglet.graphics.Batch())

        blocks_per_frame = 100
        chunks_done = []
        for cx, cz in self.chunks_to_update[:]:
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

        for chunk in chunks_done:
            if chunk in self.chunks_to_update:
                self.chunks_to_update.remove(chunk)

        self.cleanup_chunks(player_pos)

    def get_biome_label(self, player_pos):
        biome = self.getBiome(player_pos[0], player_pos[2])
        return f"Biome: {biome.capitalize()}"
        
    
    def generate_chunk_thread(self, cx, cz):
        """
        Génère un chunk avec biomes paramétrables.
        cx, cz : coordonnées du chunk
        biome_scale : plus petit = biomes plus fréquents
        biome_octaves : complexité du bruit pour bordures irrégulières
        """
        chunk_blocks = {}
        for x in range(cx*CHUNK_SIZE, (cx+1)*CHUNK_SIZE):
            for z in range(cz*CHUNK_SIZE, (cz+1)*CHUNK_SIZE):
                h = self.get_height(x, z)
                biome = self.getBiome(x, z)

                for y in range(-BLOCK_HEIGHT, h+1):
                    # Couches basses
                    if y <= 0:
                        block_type = "water"
                    elif y < h - 1:
                        if biome in ["desert", "savanna"]:
                            block_type = "sand"
                        elif biome in ["tundra", "snow", "taiga"]:
                            block_type = "stone"
                        else:
                            block_type = "dirt"
                    else:
                        # Bloc de surface : prend la texture correspondant au biome
                        block_type = biome

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


    def normalize_to_uniform_simple(self, noise_value):
        """
        Version simplifiée : transformation par fonction puissance.
        """
        normalized = (noise_value + 1) / 2  # 0..1
        
        # Transformation en forme de S pour étaler vers les extrêmes
        # Ajustez l'exposant selon vos besoins
        if normalized < 0.5:
            return 2 * (normalized ** 1.5)  # Étire vers 0
        else:
            return 1 - 2 * ((1-normalized) ** 1.5)  # Étire vers 1

    def getBiome(self, x, z, biome_scale=1000.0):
        """
        Version avec transformation simple mais efficace.
        """
        seed=WORLD_SEED
        octaves=8
        # Génération du bruit
        temp_raw = 0.7 * noise.pnoise2(x/biome_scale, z/biome_scale, octaves=octaves, base=seed) \
                + 0.3 * noise.pnoise2(x/(biome_scale/5), z/(biome_scale/5), octaves=5, base=seed+50)
        
        humid_raw = 0.7 * noise.pnoise2((x+1000)/biome_scale, (z+1000)/biome_scale, octaves=octaves, base=seed+10) \
                + 0.3 * noise.pnoise2((x+1000)/(biome_scale/5), (z+1000)/(biome_scale/5), octaves=5, base=seed+60)
        
        # Transformation pour distribution plus uniforme
        temp = self.normalize_to_uniform_simple(temp_raw)
        humid = self.normalize_to_uniform_simple(humid_raw)
        
        # Vos seuils de biomes (maintenant mieux distribués)
        if temp < 0.25:
                return "snow"
        elif temp < 0.5:
            if humid < 0.5:
                return "taiga"
            else:
                return "forest"
        elif temp < 0.75:
            if humid < 0.5:
                return "savanna"
            else:
                return "plains"
        else:
            if humid < 0.5:
                return "desert"
            else:
                return "jungle"


