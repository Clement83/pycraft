import pyglet
import os
import glob

class Textures:
    def __init__(self):
        self.textures = {}
        self.biome_textures = {}
        self.sprite_textures = {}
        self.animal_textures = {} # Ajout pour les animaux
        self.load_textures()

    def load_textures(self):
        base_path = os.path.join(os.path.dirname(__file__), "..", "assets")
        sprite_base_path = os.path.join(base_path, "sprites")
        animal_base_path = os.path.join(base_path, "annimals") # Chemin pour les animaux

        # Load general textures
        for filename in os.listdir(base_path):
            if filename.endswith(".png"):
                name = os.path.splitext(filename)[0]
                try:
                    texture = pyglet.image.load(os.path.join(base_path, filename)).get_texture()
                    self.textures[name] = texture
                    if name in ["tundra","snow","taiga","forest","plains","savanna","desert","jungle","grass","dirt","stone","water"]:
                        self.biome_textures[name] = texture
                    print(f"[Textures] Chargée : {name}")
                except Exception as e:
                    print(f"[Textures] Impossible de charger {filename} : {e}")
        
        # Load sprite textures for biomes
        if os.path.exists(sprite_base_path):
            for biome_dir in os.listdir(sprite_base_path):
                full_biome_path = os.path.join(sprite_base_path, biome_dir)
                if os.path.isdir(full_biome_path):
                    for filename in os.listdir(full_biome_path):
                        if filename.endswith(".png"):
                            sprite_name = os.path.splitext(filename)[0]
                            sprite_path = os.path.join(full_biome_path, filename)
                            try:
                                sprite_texture = pyglet.image.load(sprite_path).get_texture()
                                self.sprite_textures[f"{biome_dir}/{sprite_name}"] = sprite_texture
                                print(f"[Textures] Sprite chargé : {biome_dir}/{sprite_name}")
                            except Exception as e:
                                print(f"[Textures] Impossible de charger le sprite {biome_dir}/{filename} : {e}")

        # Load animal textures for biomes
        if os.path.exists(animal_base_path):
            for biome_dir in os.listdir(animal_base_path):
                full_biome_path = os.path.join(animal_base_path, biome_dir)
                if os.path.isdir(full_biome_path):
                    for filename in os.listdir(full_biome_path):
                        if filename.endswith(".png"):
                            animal_name = os.path.splitext(filename)[0]
                            animal_path = os.path.join(full_biome_path, filename)
                            try:
                                animal_texture = pyglet.image.load(animal_path).get_texture()
                                self.animal_textures[f"{biome_dir}/{animal_name}"] = animal_texture
                                print(f"[Textures] Animal chargé : {biome_dir}/{animal_name}")
                            except Exception as e:
                                print(f"[Textures] Impossible de charger l'animal {biome_dir}/{filename} : {e}")

    def get(self, texture_name):
        # Priorité : animaux, puis sprites, puis biomes, puis général
        if texture_name in self.animal_textures:
            return self.animal_textures[texture_name]
        if texture_name in self.sprite_textures:
            return self.sprite_textures[texture_name]
        if texture_name in self.biome_textures:
            return self.biome_textures[texture_name]
        return self.textures.get(texture_name)

    def get_biome_textures(self):
        """Retourne un dictionnaire { biome: [chemins des textures de sprites disponibles] }"""
        biome_map = {}
        for key in self.sprite_textures.keys():
            if "/" in key:
                biome_dir, sprite_name = key.split("/", 1)
                if biome_dir not in biome_map:
                    biome_map[biome_dir] = []
                biome_map[biome_dir].append(key)
        return biome_map

    def get_animal_biome_textures(self):
        """Retourne un dictionnaire { biome: [chemins des textures d'animaux disponibles] }"""
        biome_map = {}
        for key in self.animal_textures.keys():
            if "/" in key:
                biome_dir, animal_name = key.split("/", 1)
                if biome_dir not in biome_map:
                    biome_map[biome_dir] = []
                biome_map[biome_dir].append(key)
        return biome_map
