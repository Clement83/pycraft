import math
import pyglet
from pyglet.gl import *
from pyglet.window import key

from core.world import World
from core.player import Player
from core.water import WaterPlane

class Window(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_minimum_size(300, 200)
        self.world = World()
        self.player = Player((0,1,0), (-30,0))
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        pyglet.clock.schedule(self.update)
        self.set_exclusive_mouse(True)
        self.water = WaterPlane(size=2000.0)

        window = self
        self.biome_label = pyglet.text.Label('Hello, world',
                          font_name='Times New Roman',
                          font_size=18,
                          x=5, y=5,
                          anchor_x='left', anchor_y='bottom')

    def on_resize(self, width, height):
        fb_w, fb_h = self.get_framebuffer_size()
        glViewport(0, 0, fb_w, max(1, fb_h))
        return super().on_resize(width, height)

    def on_mouse_motion(self, x, y, dx, dy):
        self.player.rotation[0] -= dy / 8
        self.player.rotation[1] += dx / 8
        self.player.rotation[0] = max(-90, min(90, self.player.rotation[0]))

    def update(self, dt):
        self.player.update(dt, self.keys, self.world)
        self.world.update(self.player.position)
        self.biome_label.text = self.world.get_biome_label(self.player.position)

    def on_draw(self):
        self.clear()
        fb_w, fb_h = self.get_framebuffer_size()
        aspect = fb_w / max(1, fb_h)
        glViewport(0, 0, fb_w, fb_h)
        
        # === RENDU 3D ===
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluPerspective(65.0, aspect, 0.1, 4000.0)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        rotY = math.radians(-self.player.rotation[1])
        rotX = math.radians(self.player.rotation[0])
        look_x = math.sin(rotY)*math.cos(rotX)
        look_y = -math.sin(rotX)
        look_z = math.cos(rotY)*math.cos(rotX)
        eye = (self.player.position[0], self.player.position[1] + 0.5, self.player.position[2])
        center = (eye[0]+look_x, eye[1]+look_y, eye[2]+look_z)
        gluLookAt(eye[0], eye[1], eye[2], center[0], center[1], center[2], 0,1,0)
        
        # Rendu 3D
        self.world.draw(self.player.position)
        self.water.draw()
        if self.player.position[1] < 0:
            self.draw_underwater_filter()
        else:
            glColor4f(1.0, 1.0, 1.0, 1.0)  # couleur normale
        
        # Restaurer les matrices
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        
        # === CONFIGURATION 2D ===
        # Sauvegarder les états 3D
        glPushAttrib(GL_ENABLE_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Configuration pour le 2D
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glDisable(GL_LIGHTING)
        
        # Matrices 2D
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, fb_w, 0, fb_h, -1, 1)  # Note: 0, fb_h au lieu de fb_h, 0
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Dessiner le label
        self.biome_label.draw()
        
        # Restaurer les états 3D
        glPopAttrib()


    def draw_underwater_filter(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glColor4f(0.0, 0.3, 0.6, 0.25)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(self.width, 0)
        glVertex2f(self.width, self.height)
        glVertex2f(0, self.height)
        glEnd()

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_BLEND)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.T:
            self.player.toggle_fly()
        elif symbol == key.ESCAPE:
            self.close()

    def run(self):
        pyglet.app.run()
