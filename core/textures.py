import pyglet
import os
import glob

class Textures:
    def __init__(self):
        self.textures = {}
        self.biome_textures = {}
        self.sprite_textures = {}
        self.load_textures()

    def load_textures(self):
        base_path = os.path.join(os.path.dirname(__file__), "..", "assets")
        sprite_base_path = os.path.join(base_path, "sprites")

        # Load general textures (existing logic)
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
        
        # Load sprite textures for biomes (modified logic)
        if os.path.exists(sprite_base_path):
            for biome_dir in os.listdir(sprite_base_path):
                full_biome_path = os.path.join(sprite_base_path, biome_dir)
                if os.path.isdir(full_biome_path): # Ensure it's a directory
                    for filename in os.listdir(full_biome_path):
                        if filename.endswith(".png"):
                            sprite_name = os.path.splitext(filename)[0]
                            sprite_path = os.path.join(full_biome_path, filename)
                            try:
                                sprite_texture = pyglet.image.load(sprite_path).get_texture()
                                # Store with key like "biome_dir/sprite_name"
                                self.sprite_textures[f"{biome_dir}/{sprite_name}"] = sprite_texture
                                print(f"[Textures] Sprite chargé : {biome_dir}/{sprite_name}")
                            except Exception as e:
                                print(f"[Textures] Impossible de charger le sprite {biome_dir}/{filename} : {e}")

    def get(self, texture_name): # Renamed block_type to texture_name for clarity
        # Check sprite textures first
        if texture_name in self.sprite_textures:
            return self.sprite_textures[texture_name]
        # Then check biome textures
        if texture_name in self.biome_textures:
            return self.biome_textures[texture_name]
        # Finally, check general textures
        return self.textures.get(texture_name)

    # The get_sprite_texture method is now redundant as 'get' handles both
    # def get_sprite_texture(self, biome_name):
    #     return self.sprite_textures.get(biome_name)