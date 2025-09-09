import noise
import random
import math
from config import SPRITE_NOISE_SCALE, SPRITE_NOISE_THRESHOLD, SPRITE_HEIGHT_OFFSET, CHUNK_SIZE # Import CHUNK_SIZE as well

class Sprites:
    def __init__(self, seed=0):
        self.seed = seed
        self.sprite_positions = set() # To prevent overlapping sprites

    def has_sprite(self, x, z, biome):
        """Decides if a sprite should be placed here based on noise and biome."""
        # Use configurable noise parameters
        val = noise.pnoise2(x * SPRITE_NOISE_SCALE, z * SPRITE_NOISE_SCALE, octaves=2, base=self.seed + 100)
        val = (val + 1) / 2

        # Example: place sprites more often in plains and forest
        if biome == "plains" and val > SPRITE_NOISE_THRESHOLD:
            return True
        elif biome == "forest" and val > SPRITE_NOISE_THRESHOLD - 0.1: # Slightly more frequent in forest
            return True
        elif biome == "desert" and val > SPRITE_NOISE_THRESHOLD + 0.1: # Less frequent in desert
            return True
        elif biome == "jungle" and val > SPRITE_NOISE_THRESHOLD - 0.05:
            return True
        elif biome == "savanna" and val > SPRITE_NOISE_THRESHOLD:
            return True
        elif biome == "snow" and val > SPRITE_NOISE_THRESHOLD + 0.1:
            return True
        elif biome == "taiga" and val > SPRITE_NOISE_THRESHOLD + 0.05:
            return True
        else:
            return False

    def can_place_sprite(self, x, z, min_distance=3):
        """Checks if a sprite is too close to another sprite."""
        for sx, sz in self.sprite_positions:
            if math.hypot(sx - x, sz - z) < min_distance:
                return False
        return True

    def register_sprite(self, x, z):
        """Adds the sprite to the list of positions."""
        self.sprite_positions.add((x, z))

    def generate_for_chunk(self, chunk_x, chunk_z, world_blocks, get_biome_func):
        """Generates sprite data for a given chunk."""
        sprites_in_chunk = []
        for x in range(chunk_x * CHUNK_SIZE, (chunk_x + 1) * CHUNK_SIZE): # Use CHUNK_SIZE from config
            for z in range(chunk_z * CHUNK_SIZE, (chunk_z + 1) * CHUNK_SIZE):
                biome = get_biome_func(x, z)
                if self.has_sprite(x, z, biome) and self.can_place_sprite(x, z):
                    # Find the ground level
                    ground_y = -1
                    # Iterate downwards from max height to find the top-most solid block
                    for y in range(255, -1, -1): # Max world height 256 (0-255)
                        if (x, y, z) in world_blocks and world_blocks[(x,y,z)] != "air": # Assuming "air" is not a solid block
                            ground_y = y
                            break
                    
                    if ground_y != -1:
                        sprite_type = self.get_sprite_type_for_biome(biome)
                        if sprite_type:
                            sprites_in_chunk.append({
                                "position": (x, ground_y + SPRITE_HEIGHT_OFFSET, z), # Use configurable height offset
                                "type": sprite_type,
                                "biome": biome
                            })
                            self.register_sprite(x, z)
        return sprites_in_chunk

    def get_sprite_type_for_biome(self, biome):
        """Returns the sprite type for a given biome."""
        # This will be expanded to map biomes to specific sprite image files
        # For now, using placeholder names that correspond to the assets/sprites structure
        if biome == "plains":
            return "plains/grass" 
        elif biome == "forest":
            return "forest/grass" 
        elif biome == "desert":
            return "desert/cactus" # Assuming a cactus sprite for desert
        elif biome == "jungle":
            return "jungle/grass"
        elif biome == "savanna":
            return "savanna/savanna" # Using the exact filename from the folder structure
        elif biome == "snow":
            return "snow/glassed_grass" 
        elif biome == "taiga":
            return "taiga/glassed_grass"
        else:
            return None