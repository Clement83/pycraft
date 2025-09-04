from pyglet.gl import Config
from ui.window import Window
import pyglet
from pyglet.gl import glFrontFace, GL_CCW

if __name__ == '__main__':
    config = Config(double_buffer=True, depth_size=24, sample_buffers=1, samples=4)
    window = Window(config=config, width=800, height=600, caption='pyCraft Infinite', resizable=True)

    from pyglet.gl import glClearColor, glEnable, glDepthFunc, GL_DEPTH_TEST, GL_CULL_FACE, GL_CCW, GL_LESS
    glClearColor(0.5, 0.7, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glFrontFace(GL_CCW)
    glDepthFunc(GL_LESS)

    window.run()
