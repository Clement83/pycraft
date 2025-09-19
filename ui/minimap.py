import pyglet
from config import CHUNK_SIZE, MINIMAP_RADIUS, MINIMAP_CHUNK_PIXEL_SIZE

class Minimap:
    def __init__(self, world, textures, window_width, window_height):
        self.world = world
        self.textures = textures
        self.window_width = window_width
        self.window_height = window_height
        self.minimap_size = (MINIMAP_RADIUS * 2 + 1) * MINIMAP_CHUNK_PIXEL_SIZE

        # Create a batch for drawing the minimap to optimize rendering
        self.batch = pyglet.graphics.Batch()
        self.sprites = []

    def update_minimap(self, player_position):
        self.sprites = [] # Clear existing sprites
        player_chunk_x = int(player_position[0] // CHUNK_SIZE)
        player_chunk_z = int(player_position[2] // CHUNK_SIZE)

        # Calculate minimap position (centered)
        minimap_x_offset = (self.window_width - self.minimap_size) // 2
        minimap_y_offset = (self.window_height - self.minimap_size) // 2

        for dx in range(-MINIMAP_RADIUS, MINIMAP_RADIUS + 1):
            for dz in range(-MINIMAP_RADIUS, MINIMAP_RADIUS + 1):
                cx, cz = player_chunk_x + dx, player_chunk_z + dz
                
                # Get biome at chunk center
                biome_name = self.world.get_biome_at_chunk_center(cx, cz)
                biome_texture = self.textures.get(biome_name)

                if biome_texture:
                    # Calculate position on the minimap grid
                    sprite_x = minimap_x_offset + (dx + MINIMAP_RADIUS) * MINIMAP_CHUNK_PIXEL_SIZE
                    sprite_y = minimap_y_offset + (dz + MINIMAP_RADIUS) * MINIMAP_CHUNK_PIXEL_SIZE
                    
                    # Create a sprite for the biome texture
                    sprite = pyglet.sprite.Sprite(biome_texture, x=sprite_x, y=sprite_y, batch=self.batch)
                    sprite.scale = MINIMAP_CHUNK_PIXEL_SIZE / sprite.width # Scale to MINIMAP_CHUNK_PIXEL_SIZE
                    self.sprites.append(sprite)

    def draw(self):
        # Calculate minimap position (centered) - recalculate to ensure it's always up-to-date
        minimap_x_offset = (self.window_width - self.minimap_size) // 2
        minimap_y_offset = (self.window_height - self.minimap_size) // 2

        # Draw the minimap background
        pyglet.shapes.Rectangle(
            minimap_x_offset - 5,
            minimap_y_offset - 5,
            self.minimap_size + 10,
            self.minimap_size + 10,
            color=(0, 0, 0, 128) # Semi-transparent black background
        ).draw()

        self.batch.draw()

        # Draw player indicator
        player_indicator_x = minimap_x_offset + MINIMAP_RADIUS * MINIMAP_CHUNK_PIXEL_SIZE + (MINIMAP_CHUNK_PIXEL_SIZE // 2)
        player_indicator_y = minimap_y_offset + MINIMAP_RADIUS * MINIMAP_CHUNK_PIXEL_SIZE + (MINIMAP_CHUNK_PIXEL_SIZE // 2)
        pyglet.shapes.Circle(player_indicator_x, player_indicator_y, MINIMAP_CHUNK_PIXEL_SIZE // 4, color=(255, 0, 0)).draw()
