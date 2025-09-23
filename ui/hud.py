import pyglet
from pyglet import shapes

class HUD:
    def __init__(self):
        self.temp_label = pyglet.text.Label(
            '', font_name='Arial', font_size=12,
            x=10, y=10, anchor_x='left', anchor_y='bottom'
        )
        self.humid_label = pyglet.text.Label(
            '', font_name='Arial', font_size=12,
            x=10, y=30, anchor_x='left', anchor_y='bottom'
        )
        self.selected_block_sprite = None
    def draw(self, window_width, window_height, temp=0.0, humid=0.0, selected_block_texture=None):
        # Draw crosshair
        crosshair_size = 10
        crosshair_thickness = 2
        center_x = window_width / 2
        center_y = window_height / 2

        shapes.Rectangle(center_x - crosshair_size, center_y - crosshair_thickness / 2,
                           crosshair_size * 2, crosshair_thickness,
                           color=(255, 255, 255, 255)).draw()
        shapes.Rectangle(center_x - crosshair_thickness / 2, center_y - crosshair_size,
                           crosshair_thickness, crosshair_size * 2,
                           color=(255, 255, 255, 255)).draw()

        # Update and draw labels
        self.temp_label.text = f"Temperature: {temp:.2f}"
        self.humid_label.text = f"Humidity: {humid:.2f}"
        self.temp_label.draw()
        self.humid_label.draw()

        # Draw selected block texture
        if selected_block_texture:
            if not self.selected_block_sprite or self.selected_block_sprite.image != selected_block_texture:
                self.selected_block_sprite = pyglet.sprite.Sprite(selected_block_texture)
                self.selected_block_sprite.scale = 2.0 # Make it bigger

            # Position it next to the selected block label (which is at y=30)
            self.selected_block_sprite.x = window_width / 2 + 100
            self.selected_block_sprite.y = 30
            self.selected_block_sprite.draw()
