import pyglet
import os

class Textures:
    def __init__(self):
        self.textures = {}
        self.biome_textures = {}
        self.load_textures()

    def load_textures(self):
        base_path = os.path.join(os.path.dirname(__file__), "..", "assets")

        for filename in os.listdir(base_path):
            if filename.endswith(".png"):
                name = os.path.splitext(filename)[0]  # nom sans extension
                try:
                    texture = pyglet.image.load(os.path.join(base_path, filename)).get_texture()
                    self.textures[name] = texture

                    # Si le nom du fichier correspond à un biome, on l’ajoute aussi au mapping biome
                    if name in ["tundra","snow","taiga","forest","plains","savanna","desert","jungle","jungle","grass","dirt","stone","water"]:
                        self.biome_textures[name] = texture

                    print(f"[Textures] Chargée : {name}")
                except Exception as e:
                    print(f"[Textures] Impossible de charger {filename} : {e}")

    def get(self, block_type):
        # Si c’est un biome, renvoie la texture correspondante
        if block_type in self.biome_textures:
            return self.biome_textures[block_type]
        return self.textures.get(block_type)

