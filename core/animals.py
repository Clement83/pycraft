import random
from config import CHUNK_SIZE
from config import ANIMAL_NOISE_SCALE, ANIMAL_NOISE_THRESHOLD, ANIMAL_HEIGHT_OFFSET, SPRITE_HEIGHT_OFFSET, CHUNK_SIZE # Import CHUNK_SIZE as well

class Animals:
    def __init__(self, seed=0):
        self.seed = seed
        self.animal_positions = set()
        self.textures = None  # Sera défini depuis World

    def set_textures(self, textures):
        self.textures = textures

    def hash_noise(self, x, z, seed):
        r = random.Random((x * 83756093) ^ (z * 29349663) ^ seed)
        return r.random()

    def has_animal(self, x, z, h, biome):
        """Décide si un animal doit apparaître ici."""
        # Les animaux sont plus rares que les sprites d'herbe
        val = self.hash_noise(x, z, self.seed)

        if h < -2 and val > ANIMAL_NOISE_THRESHOLD - 0.02: # More likely underwater
            return True
        elif h < 0:
            return False
        # Example: place sprites more often in plains and forest
        elif biome == "plains" and val > ANIMAL_NOISE_THRESHOLD:
            return True
        elif biome == "forest" and val > (ANIMAL_NOISE_THRESHOLD - 0.1): # Slightly more frequent in forest
            return True
        elif biome == "desert" and val > (ANIMAL_NOISE_THRESHOLD + 0.04): # Less frequent in desert
            return True
        elif biome == "jungle" and val > (ANIMAL_NOISE_THRESHOLD - 0.2):
            return True
        elif biome == "savanna" and val > ANIMAL_NOISE_THRESHOLD:
            return True
        elif biome == "snow" and val > (ANIMAL_NOISE_THRESHOLD + 0.03):
            return True
        elif biome == "taiga" and val > (ANIMAL_NOISE_THRESHOLD + 0.01):
            return True
        else:
            return False

    def register_animal(self, x, z):
        self.animal_positions.add((x, z))

    def generate_for_chunk(self, chunk_x, chunk_z, get_height_func, get_biome_func):
        """Génère les données des animaux pour un chunk."""
        animals_in_chunk = []
        for x in range(chunk_x * CHUNK_SIZE, (chunk_x + 1) * CHUNK_SIZE):
            for z in range(chunk_z * CHUNK_SIZE, (chunk_z + 1) * CHUNK_SIZE):
                biome = get_biome_func(x, z)
                ground_y = get_height_func(x, z)

                if self.has_animal(x, z, ground_y, biome):
                    animal_type = self.get_animal_type_for_biome(biome, ground_y, x, z)
                    if animal_type:
                        animals_in_chunk.append({
                            "position": (x, ground_y + ANIMAL_HEIGHT_OFFSET, z), # Un peu au-dessus du sol
                            "type": animal_type,
                            "biome": biome
                        })
                        self.register_animal(x, z)
        return animals_in_chunk

    def get_animal_type_for_biome(self, biome, ground_y, x=None, z=None):
        """Retourne un type d'animal pour un biome donné."""
        if not self.textures:
            return None

        # Utilise une nouvelle méthode de textures pour les animaux
        animal_map = self.textures.get_animal_biome_textures()

        if ground_y < 0:
            biome = "water"

        animals_for_biome = animal_map.get(biome, [])
        if not animals_for_biome:
            return None

        # Sélection déterministe
        if x is not None and z is not None:
            val = self.hash_noise(x, z, self.seed + 200)
            idx = int(val * len(animals_for_biome))
            return animals_for_biome[idx]
        else:
            return random.choice(animals_for_biome)
