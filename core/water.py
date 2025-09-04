import time
import ctypes
from pyglet.gl import *

class WaterPlane:
    def __init__(self, height=0.0, size=200.0):
        self.height = height
        self.size = size

        # Créer un quad simple
        s = self.size / 2
        h = self.height
        self.vertices = [
            -s, h, -s,  # coin bas-gauche
            -s, h,  s,  # coin haut-gauche
             s, h,  s,  # coin haut-droite
             s, h, -s   # coin bas-droite
        ]

        # Vertex shader
        vertex_src = """
        #version 120
        attribute vec3 position;
        varying vec2 v_uv;
        void main() {
            v_uv = position.xz * 0.05;
            gl_Position = gl_ModelViewProjectionMatrix * vec4(position, 1.0);
        }
        """

        # Fragment shader (scintillement)
        fragment_src = """
        #version 120
        uniform float u_time;
        varying vec2 v_uv;
        void main() {
            float flicker = 0.5 + 0.5 * sin(u_time*3.0 + gl_FragCoord.x*0.05 + gl_FragCoord.y*0.05);
            vec3 color = vec3(0.2, 0.4, 0.8) * flicker;
            gl_FragColor = vec4(color, 0.8);
        }
        """

        self.program = self.create_shader(vertex_src, fragment_src)
        self.time_loc = glGetUniformLocation(self.program, b"u_time")

    def create_shader(self, vs_source, fs_source):
        def compile_shader(src, shader_type):
            shader = glCreateShader(shader_type)
            src_buffer = ctypes.create_string_buffer(src.encode('utf-8'))
            src_ptr = ctypes.cast(ctypes.pointer(src_buffer), ctypes.POINTER(ctypes.c_char))
            src_pp = ctypes.pointer(ctypes.cast(src_ptr, ctypes.POINTER(ctypes.c_char)))
            length = ctypes.c_int(len(src))
            glShaderSource(shader, 1, src_pp, ctypes.byref(length))
            glCompileShader(shader)

            status = ctypes.c_int()
            glGetShaderiv(shader, GL_COMPILE_STATUS, ctypes.byref(status))
            if not status.value:
                log_length = ctypes.c_int()
                glGetShaderiv(shader, GL_INFO_LOG_LENGTH, ctypes.byref(log_length))
                log = ctypes.create_string_buffer(log_length.value)
                glGetShaderInfoLog(shader, log_length, None, log)
                raise RuntimeError("Shader compile error: " + log.value.decode(errors="ignore"))
            return shader

        vs = compile_shader(vs_source, GL_VERTEX_SHADER)
        fs = compile_shader(fs_source, GL_FRAGMENT_SHADER)

        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        status = ctypes.c_int()
        glGetProgramiv(program, GL_LINK_STATUS, ctypes.byref(status))
        if not status.value:
            log_length = ctypes.c_int()
            glGetProgramiv(program, GL_INFO_LOG_LENGTH, ctypes.byref(log_length))
            log = ctypes.create_string_buffer(log_length.value)
            glGetProgramInfoLog(program, log_length, None, log)
            raise RuntimeError("Shader link error: " + log.value.decode(errors="ignore"))

        return program

    def draw(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glUseProgram(self.program)

        t = time.time()
        glUniform1f(self.time_loc, t)

        glDisable(GL_CULL_FACE)  # Voir le quad des deux côtés

        glBegin(GL_QUADS)
        glVertex3f(self.vertices[0], self.vertices[1], self.vertices[2])
        glVertex3f(self.vertices[3], self.vertices[4], self.vertices[5])
        glVertex3f(self.vertices[6], self.vertices[7], self.vertices[8])
        glVertex3f(self.vertices[9], self.vertices[10], self.vertices[11])
        glEnd()

        glEnable(GL_CULL_FACE)
        glUseProgram(0)
        glDisable(GL_BLEND)
