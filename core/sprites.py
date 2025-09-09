import noise
import random
import math
from config import SPRITE_NOISE_SCALE, SPRITE_NOISE_THRESHOLD, SPRITE_HEIGHT_OFFSET, CHUNK_SIZE # Import CHUNK_SIZE as well

class Sprites:
    def __init__(self, seed=0):
        self.seed = seed
        self.sprite_positions = set() # To prevent overlapping sprites

    def hash_noise(self, x, z, seed):
        r = random.Random((x * 73856093) ^ (z * 19349663) ^ seed)
        return r.random() * 2 - 1  # entre -1 et 1
        
    def has_sprite(self, x, z, h, biome):
        """Decides if a sprite should be placed here based on noise and biome."""
        # Use configurable noise parameters
        val = self.hash_noise(x, z, self.seed)
        val = (val + 1) / 2

        if h < -2 and val > SPRITE_NOISE_THRESHOLD + 0.2: # More likely underwater
            print(f"Placing underwater sprite at ({x}, {h}, {z}) in biome {biome} with noise value {val}")
            return True
        elif h < 0:
            return False
        # Example: place sprites more often in plains and forest
        elif biome == "plains" and val > SPRITE_NOISE_THRESHOLD:
            return True
        elif biome == "forest" and val > (SPRITE_NOISE_THRESHOLD - 0.1): # Slightly more frequent in forest
            return True
        elif biome == "desert" and val > (SPRITE_NOISE_THRESHOLD + 0.25): # Less frequent in desert
            return True
        elif biome == "jungle" and val > (SPRITE_NOISE_THRESHOLD - 0.05):
            return True
        elif biome == "savanna" and val > SPRITE_NOISE_THRESHOLD:
            return True
        elif biome == "snow" and val > (SPRITE_NOISE_THRESHOLD + 0.1):
            return True
        elif biome == "taiga" and val > (SPRITE_NOISE_THRESHOLD + 0.05):
            return True
        else:
            return False

    def can_place_sprite(self, x, z, min_distance=3):
        """Checks if a sprite is too close to another sprite."""
        # for sx, sz in self.sprite_positions:
        #     if math.hypot(sx - x, sz - z) < min_distance:
        #         return False
        return True

    def register_sprite(self, x, z):
        """Adds the sprite to the list of positions."""
        self.sprite_positions.add((x, z))

    def generate_for_chunk(self, chunk_x, chunk_z, get_height_func, get_biome_func):
        """Generates sprite data for a given chunk."""
        sprites_in_chunk = []
        for x in range(chunk_x * CHUNK_SIZE, (chunk_x + 1) * CHUNK_SIZE): # Use CHUNK_SIZE from config
            for z in range(chunk_z * CHUNK_SIZE, (chunk_z + 1) * CHUNK_SIZE):
                biome = get_biome_func(x, z)
                # Find the ground level
                ground_y = get_height_func(x, z)
                if self.has_sprite(x, z, ground_y, biome) and self.can_place_sprite(x, z):
                    
                    sprite_type = self.get_sprite_type_for_biome(biome, ground_y)
                    if sprite_type:
                        sprites_in_chunk.append({
                            "position": (x, ground_y + SPRITE_HEIGHT_OFFSET, z), # Use configurable height offset
                            "type": sprite_type,
                            "biome": biome
                        })
                        self.register_sprite(x, z)
        return sprites_in_chunk

    def get_sprite_type_for_biome(self, biome, ground_y):
        """Returns the sprite type for a given biome."""
        # This will be expanded to map biomes to specific sprite image files
        # For now, using placeholder names that correspond to the assets/sprites structure

        if ground_y < 0:
            return "water/algae"
        elif biome == "plains":
            return "plains/grass" 
        elif biome == "forest":
            return "forest/grass" 
        elif biome == "desert":
            return "desert/desert" # Assuming a cactus sprite for desert
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