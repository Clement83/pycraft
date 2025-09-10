import random
import math
import os
from config import ANIMAL_RENDER_DISTANCE, CHUNK_SIZE, ANIMAL_HEIGHT_OFFSET

# Import des classes d'animaux
from core.animal.base import BaseAnimal
from core.animal.poisson import Poisson
from core.animal.poulpe import Poulpe
from core.animal.giraf import Giraf
from core.animal.frog import Frog

# Classe manager pour tous les animaux
class Animals:
    def __init__(self, seed=0):
        self.seed = seed
        self.active_animals = []
        self.textures = None
        self.max_animals = 30
        self.spawn_radius = ANIMAL_RENDER_DISTANCE * CHUNK_SIZE / 2
        self.r = random.Random(seed)
        
        # Mapper le nom du type d'animal (depuis le nom de fichier) à la classe
        self.animal_class_map = {
            "fish1": Poisson,
            "poulpe": Poulpe,
            "giraf1": Giraf,
            "frog": Frog
        }

    def set_textures(self, textures):
        self.textures = textures

    def update(self, dt, player_pos, world_info_funcs):
        """Méthode principale appelée à chaque frame."""
        self._manage_population(player_pos, world_info_funcs.get("get_height"), world_info_funcs.get("get_biome"))

        # Le dictionnaire est déjà prêt à être passé aux animaux
        for animal in self.active_animals:
            animal.update(dt, player_pos, world_info_funcs)

        player_x, _, player_z = player_pos
        max_dist = self.spawn_radius * 1.5
        self.active_animals = [
            animal for animal in self.active_animals 
            if math.hypot(animal.x - player_x, animal.z - player_z) < max_dist
        ]

    def _manage_population(self, player_pos, get_height_func, get_biome_func):
        if len(self.active_animals) < self.max_animals:
            self._spawn_animal(player_pos, get_height_func, get_biome_func)

    def _spawn_animal(self, player_pos, get_height_func, get_biome_func):
        player_x, _, player_z = player_pos
        for _ in range(10):
            angle = self.r.uniform(0, 2 * math.pi)
            dist = self.r.uniform(self.spawn_radius / 2, self.spawn_radius)
            x = int(player_x + dist * math.cos(angle))
            z = int(player_z + dist * math.sin(angle))
            h = get_height_func(x, z)
            biome = get_biome_func(x, z)

            if h < 0:
                biome = "water"

            animal_texture_path = self.get_animal_type_for_biome(biome)
            if animal_texture_path:
                # Extraire le nom de base de la texture pour trouver la classe
                type_name = os.path.splitext(os.path.basename(animal_texture_path))[0]
                # Utiliser BaseAnimal comme fallback si le type n'est pas dans la map
                AnimalClass = self.animal_class_map.get(type_name, BaseAnimal)

                new_animal = AnimalClass(x, h + 1, z, animal_texture_path)
                self.active_animals.append(new_animal)
                return

    def get_animal_type_for_biome(self, biome):
        if not self.textures:
            return None
        animal_map = self.textures.get_animal_biome_textures()
        animals_for_biome = animal_map.get(biome, [])
        if not animals_for_biome:
            return None
        return self.r.choice(animals_for_biome)

    def get_render_data(self):
        return [
            {"position": (animal.x, animal.y, animal.z), "type": animal.type, "velocity": animal.velocity, "width": animal.width, "height": animal.height}
            for animal in self.active_animals
        ]
