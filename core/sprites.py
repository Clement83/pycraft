import noise
import random
import math
from config import SPRITE_NOISE_SCALE, SPRITE_NOISE_THRESHOLD, SPRITE_HEIGHT_OFFSET, CHUNK_SIZE # Import CHUNK_SIZE as well
from core.textures import Textures
from core.vegetation import Vegetation

class Sprites:
    def __init__(self, seed=0, vegetation = None, textures=None):
        self.seed = seed
        self.sprite_positions = set() # To prevent overlapping sprites
        self.textures = textures
        self.vegetation = vegetation

    def hash_noise(self, x, z, seed):
        r = random.Random((x * 73856093) ^ (z * 19349663) ^ seed)
        return r.random()  # entre 0 et 1
        
    def has_sprite(self, x, z, h, biome):
        """Decides if a sprite should be placed here based on noise and biome."""
        
        if self.vegetation.has_tree(x, z, biome):
            return False # No sprites where there are trees

        val = self.hash_noise(x, z, self.seed)

        if h < -2 and val > SPRITE_NOISE_THRESHOLD - 0.2: # More likely underwater
            return True
        if h == -1 and val > SPRITE_NOISE_THRESHOLD:
            return True
        elif h < 0:
            return False
        # Example: place sprites more often in plains and forest
        elif biome == "plains" and val > SPRITE_NOISE_THRESHOLD:
            return True
        elif biome == "forest" and val > (SPRITE_NOISE_THRESHOLD - 0.1): # Slightly more frequent in forest
            return True
        elif biome == "desert" and val > (SPRITE_NOISE_THRESHOLD + 0.15): # Less frequent in desert
            return True
        elif biome == "jungle" and val > (SPRITE_NOISE_THRESHOLD - 0.18):
            return True
        elif biome == "savanna" and val > SPRITE_NOISE_THRESHOLD:
            return True
        elif biome == "snow" and val > (SPRITE_NOISE_THRESHOLD + 0.18):
            return True
        elif biome == "taiga" and val > (SPRITE_NOISE_THRESHOLD + 0.08):
            return True
        else:
            return False

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
                if self.has_sprite(x, z, ground_y, biome):

                    sprite_type = self.get_sprite_type_for_biome(biome, ground_y, x, z)
                    if sprite_type:
                        sprites_in_chunk.append({
                            "position": (x, ground_y + SPRITE_HEIGHT_OFFSET, z), # Use configurable height offset
                            "type": sprite_type,
                            "biome": biome
                        })
                        self.register_sprite(x, z)
        return sprites_in_chunk

    def get_sprite_type_for_biome(self, biome, ground_y, x=None, z=None):
        """
        Retourne une texture pour un biome donné en utilisant le bruit (sélection déterministe).
        Cas spécial : si ground_y < 0 → biome = "water".
        """
        if not self.textures:
            print(f"[Sprites] Aucun gestionnaire de textures fourni pour biome={biome}")
            return None

        biome_map = self.textures.get_biome_textures()

        # Cas spécial : sous l'eau -> forcer biome = water
        if ground_y < 0:
            biome = "water"
        
        if ground_y == -1:
            biome = "plage"

        textures_for_biome = biome_map.get(biome, [])
        # TODO  remove texture leaves and log from sprite selection
        textures_for_biome = [tex for tex in textures_for_biome if "leaves" not in tex and "log" not in tex]
        if not textures_for_biome:
            return None  # aucun sprite dispo pour ce biome

        # Sélection déterministe via bruit
        if x is not None and z is not None:
            val = self.hash_noise(x, z, self.seed + 100) 
            idx = int(val * len(textures_for_biome)) % len(textures_for_biome)
            chosen = textures_for_biome[idx]
        else:
            # fallback si pas de coordonnées (rare)
            chosen = random.choice(textures_for_biome)
        return chosen
