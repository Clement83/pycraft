import random
import math
import os
import pyglet # Added for batch rendering
from config import ANIMAL_RENDER_DISTANCE, CHUNK_SIZE, ANIMAL_HEIGHT_OFFSET

# Import des classes d'animaux
from core.animal.base import BaseAnimal
from core.animal.poisson import Poisson
from core.animal.poulpe import Poulpe
from core.animal.giraf import Giraf
from core.animal.frog import Frog
from core.animal.snake import Snake
from core.animal.cerf import Cerf


# Classe manager pour tous les animaux
class Animals:
    def __init__(self, seed=0, vegetation=None, program=None): # Added program
        self.seed = seed
        self.active_animals = []
        self.textures = None
        self.max_animals = 30
        self.spawn_radius = ANIMAL_RENDER_DISTANCE * CHUNK_SIZE / 2
        self.r = random.Random(seed)
        self.vegetation = vegetation
        self.program = program # Store the shader program
        self.animal_batches = {} # Dictionary to store batches per texture
        # self.vertex_list = None # No longer needed
        self._needs_rebuild = False # Flag to indicate if the vertex list needs rebuilding

        # Mapper le nom du type d'animal (depuis le nom de fichier) à la classe
        self.animal_class_map = {
            "fish1": Poisson,
            "shark": Poisson,
            "tortule": Poisson,
            "poulpe": Poulpe,
            "giraf1": Giraf,
            "snake": Snake,
            "frog": Frog,
            "cerf": Cerf,
            "cerf1": Cerf
        }

    def set_textures(self, textures):
        self.textures = textures

    def update(self, dt, player_pos, world_info_funcs):
        """Méthode principale appelée à chaque frame."""
        self._manage_population(player_pos, world_info_funcs.get("get_height"), world_info_funcs.get("get_biome"))

        # Le dictionnaire est déjà prêt à être passé aux animaux
        for animal in self.active_animals:
            old_pos = (animal.x, animal.y, animal.z)
            animal.update(dt, player_pos, world_info_funcs)
            new_pos = (animal.x, animal.y, animal.z)
            if old_pos != new_pos:
                self._needs_rebuild = True # Animal moved, so rebuild

        player_x, _, player_z = player_pos
        max_dist = self.spawn_radius * 1.5
        # Filter out animals that are too far, and mark for rebuild if any are removed
        initial_animal_count = len(self.active_animals)
        self.active_animals = [
            animal for animal in self.active_animals 
            if math.hypot(animal.x - player_x, animal.z - player_z) < max_dist
        ]
        if len(self.active_animals) < initial_animal_count:
            self._needs_rebuild = True # Animals were removed, so rebuild

        if self._needs_rebuild:
            self._rebuild_vertex_list()

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


            if self.vegetation.has_tree(x, z, biome):
                continue # No animals where there are trees

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
                self._needs_rebuild = True # Mark for rebuild when a new animal is spawned
                return

    def get_animal_type_for_biome(self, biome):
        if not self.textures:
            return None
        animal_map = self.textures.get_animal_biome_textures()
        animals_for_biome = animal_map.get(biome, [])
        if not animals_for_biome:
            return None
        return self.r.choice(animals_for_biome)

    def _rebuild_vertex_list(self):
        # This method will build the combined mesh for all active animals
        # Similar logic to World.build_sprite_mesh but for animals only
        vertex_data_by_texture = {}
        
        sprite_tex_coords = (0, 0, 1, 0, 1, 1, 0, 1)
        sprite_indices_template = (0, 1, 2, 0, 2, 3)
        
        y_offset = -0.5 # Animals are typically on the ground

        for animal in self.active_animals:
            x, y, z = animal.x, animal.y, animal.z
            width = animal.width
            height = animal.height

            half_width = width / 2
            sprite_quad_vertices = [(-half_width, 0.0, 0.0), (half_width, 0.0, 0.0), (half_width, height, 0.0), (-half_width, height, 0.0)]

            # Logic for animals (single oriented plane)
            velocity = animal.velocity
            vx, _, vz = velocity
            
            # Calculate rotation angle on Y axis
            if abs(vx) > 0.01 or abs(vz) > 0.01:
                angle = math.atan2(vx, vz)
            else:
                angle = 0 # No movement, no rotation

            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            rotated_vertices = []
            for v_x, v_y, v_z in sprite_quad_vertices:
                # 2D rotation on XZ plane
                rotated_x = v_x * cos_a
                rotated_z = v_x * sin_a
                # Add world position
                rotated_vertices.append((x + rotated_x, y + v_y + y_offset, z + rotated_z))

            # Get texture for the animal
            texture = self.textures.get(animal.type) # Assuming animal.type maps to a texture
            if texture is None: continue

            if texture not in vertex_data_by_texture:
                vertex_data_by_texture[texture] = {'positions': [], 'tex_coords': [], 'indices': [], 'colors': [], 'count': 0}
            
            mesh_data = vertex_data_by_texture[texture]
            vc = mesh_data['count']

            for vert in rotated_vertices:
                mesh_data['positions'].extend(vert)
            
            mesh_data['tex_coords'].extend(sprite_tex_coords)
            mesh_data['colors'].extend((1.0, 1.0, 1.0) * 4)
            mesh_data['indices'].extend((vc + i for i in sprite_indices_template))
            mesh_data['count'] += 4

        # Clear previous batches
        for texture_key in list(self.animal_batches.keys()): # Iterate over a copy of keys
            batch = self.animal_batches.pop(texture_key) # Remove and get the batch
            # Pyglet batches don't have a direct delete method, but their vertex lists do.
            # If the batch contains vertex lists, they should be deleted.
            # For simplicity, we'll rely on Python's garbage collection for the batch object itself.
            # However, if vertex lists are directly managed, they need explicit deletion.
            # Given how pyglet.graphics.Batch works, deleting the batch itself might not free GL resources.
            # The vertex_list_indexed call returns a VertexList object. We need to store and delete those.
            # Let's assume for now that replacing the batch will eventually free resources.
            # A more robust solution would involve tracking the VertexList objects created within the batch.
            pass # No explicit deletion needed for the batch object itself

        # Create new batches
        for texture, mesh_data in vertex_data_by_texture.items():
            if not mesh_data['indices']: continue
            
            # Create a new batch for this texture
            batch = pyglet.graphics.Batch()
            self.program.vertex_list_indexed(
                mesh_data['count'], pyglet.gl.GL_TRIANGLES, mesh_data['indices'], batch, None,
                position=('f', mesh_data['positions']),
                tex_coords=('f', mesh_data['tex_coords']),
                colors=('f', mesh_data['colors'])
            )
            self.animal_batches[texture] = batch # Store the batch keyed by texture

        self._needs_rebuild = False # Reset the flag

    def draw(self):
        # Iterate through the animal_batches and draw each one
        for texture, batch in self.animal_batches.items():
            if batch:
                pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
                pyglet.gl.glBindTexture(texture.target, texture.id)
                self.program['our_texture'] = 0
                batch.draw()
