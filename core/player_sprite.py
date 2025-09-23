import pyglet
import random
import os
import math # Added for billboard calculations
from pyglet.math import Mat4, Vec3 # Added for matrix operations

class PlayerSprite:
    def __init__(self, position=(0, 0, 0), rotation=(0, 0), program=None): # Added program
        self.position = list(position)
        self.rotation = list(rotation)
        self.program = program # Store the shader program

        # List of available animal sprites
        animal_sprites = [
            "assets/annimals/savanna/lion.png",
            "assets/annimals/plains/sheep.png",
            "assets/annimals/taiga/wolf.png",
            "assets/annimals/snow/renardArtic.png",
            "assets/annimals/snow/pinguin.png",
            "assets/annimals/desert/iguan.png",
            "assets/annimals/forest/cerf.png",
            "assets/annimals/forest/frog.png",
            "assets/annimals/forest/renard.png",
            "assets/annimals/jungle/frog.png",
            "assets/annimals/jungle/snake.png",
            "assets/annimals/plains/frog.png",
            "assets/annimals/savanna/giraf1.png",
            "assets/annimals/taiga/frog.png",
            "assets/annimals/sea_floor/fish1.png",
            "assets/annimals/sea_floor/poulpe.png"        ]

        # Choose a random animal sprite
        chosen_sprite_path = random.choice(animal_sprites)

        try:
            self.texture = pyglet.image.load(chosen_sprite_path).get_texture()
            # Set texture parameters for pixel art
            pyglet.gl.glBindTexture(self.texture.target, pyglet.gl.GL_TEXTURE_2D) # Use GL_TEXTURE_2D
            pyglet.gl.glTexParameteri(self.texture.target, pyglet.gl.GL_TEXTURE_MAG_FILTER, pyglet.gl.GL_NEAREST)
            pyglet.gl.glTexParameteri(self.texture.target, pyglet.gl.GL_TEXTURE_MIN_FILTER, pyglet.gl.GL_NEAREST)
        except Exception as e:
            print(f"Error loading sprite texture {chosen_sprite_path}: {e}")
            self.texture = None

        # Define quad vertices (centered at 0,0,0, will be translated to self.position)
        # A simple quad for a billboarded sprite
        # Assuming sprite is 1 unit wide and 1 unit tall for now, adjust as needed
        width = 1.0
        height = 1.0
        half_width = width / 2.0

        # Vertices for a quad facing the positive Z axis (will be rotated to face camera)
        # (x, y, z)
        self.base_vertices = [
            -half_width, 0.0, 0.0,  # Bottom-left
             half_width, 0.0, 0.0,  # Bottom-right
             half_width, height, 0.0, # Top-right
            -half_width, height, 0.0   # Top-left
        ]

        self.tex_coords = [
            0.0, 0.0,  # Bottom-left
            1.0, 0.0,  # Bottom-right
            1.0, 1.0,  # Top-right
            0.0, 1.0   # Top-left
        ]

        self.colors = [
            1.0, 1.0, 1.0, 1.0, # White
            1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0
        ]

        self.indices = [0, 1, 2, 0, 2, 3] # Two triangles for the quad

        self.batch = pyglet.graphics.Batch()
        self.vertex_list = None
        # Initial update will be called from Client.py after program is available

    def update_sprite_position(self, view_matrix=None):
        if not self.program or not self.texture:
            return

        # Calculate billboarded vertices
        transformed_vertices = []
        if view_matrix is not None: # Check if view_matrix is provided
            # Extract camera's right and up vectors from the view matrix
            right_vec = Vec3(view_matrix[0], view_matrix[4], view_matrix[8])
            up_vec = Vec3(view_matrix[1], view_matrix[5], view_matrix[9])

            # Scale right and up vectors by half_width and height
            width = 1.0 # Assuming 1 unit width
            height = 1.0 # Assuming 1 unit height
            half_width = width / 2.0

            # Vertices relative to sprite's center
            # Bottom-left, Bottom-right, Top-right, Top-left
            offsets = [
                (-half_width, 0.0),
                (half_width, 0.0),
                (half_width, height),
                (-half_width, height)
            ]

            for ox, oy in offsets:
                # Calculate vertex position in world space
                # Start from sprite's base position (self.position)
                # Add offset along right_vec and up_vec
                vertex_pos = Vec3(self.position[0], self.position[1], self.position[2]) + \
                             right_vec * ox + \
                             up_vec * oy
                transformed_vertices.extend(vertex_pos.xyz)
        else:
            # If no view_matrix, just use the base vertices translated by position
            for i in range(0, len(self.base_vertices), 3):
                transformed_vertices.extend([
                    self.base_vertices[i] + self.position[0],
                    self.base_vertices[i+1] + self.position[1],
                    self.base_vertices[i+2] + self.position[2]
                ])

        if self.vertex_list:
            self.vertex_list.delete()

        self.vertex_list = self.program.vertex_list_indexed(
            4, pyglet.gl.GL_TRIANGLES, self.indices, self.batch, None,
            position=('f', transformed_vertices),
            tex_coords=('f', self.tex_coords),
            colors=('f', self.colors)
        )

    def draw(self):
        if self.vertex_list and self.texture and self.program:
            self.program.use()
            pyglet.gl.glActiveTexture(pyglet.gl.GL_TEXTURE0)
            pyglet.gl.glBindTexture(self.texture.target, self.texture.id)
            self.program['our_texture'] = 0 # Assuming 'our_texture' is the uniform name

            # Enable blending for transparency
            pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
            pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)

            # Disable face culling for billboards (both sides should be visible)
            pyglet.gl.glDisable(pyglet.gl.GL_CULL_FACE)

            self.batch.draw()

            # Restore previous OpenGL states
            pyglet.gl.glDisable(pyglet.gl.GL_BLEND)
            pyglet.gl.glEnable(pyglet.gl.GL_CULL_FACE) # Re-enable culling for other objects
            self.program.stop()

    def update(self, position, rotation, view_matrix=None): # Added view_matrix
        self.position = list(position)
        self.rotation = list(rotation)
        self.update_sprite_position(view_matrix) # Pass view_matrix
