import pyglet
from pyglet import shapes

class HUD:
    def __init__(self):
        pass

    def draw(self, window_width, window_height):
        # Draw crosshair
        crosshair_size = 10
        crosshair_thickness = 2 # This will be the width/height of the rectangles
        center_x = window_width / 2
        center_y = window_height / 2

        # Horizontal part (rectangle)
        shapes.Rectangle(center_x - crosshair_size, center_y - crosshair_thickness / 2,
                           crosshair_size * 2, crosshair_thickness,
                           color=(255, 255, 255, 255)).draw()
        # Vertical part (rectangle)
        shapes.Rectangle(center_x - crosshair_thickness / 2, center_y - crosshair_size,
                           crosshair_thickness, crosshair_size * 2,
                           color=(255, 255, 255, 255)).draw()
